#!/usr/bin/env python3
"""
Scrape county board supervisors from the 57 Wisconsin counties whose roster this
file can reach. Stage 1 of the pair; build_wi_county_board_roster.py turns the
intermediate JSON into data/app/county-board-members.json.

TWELVE ROUTES, AND WHICH ONE A COUNTY TAKES IS A MEASUREMENT
------------------------------------------------------------
  * COUNTIES                    - 41 counties whose own board page pairs a
                                  district with a person, each page's reading
                                  direction PINNED;
  * ARCGIS_COUNTIES             - Milwaukee and Racine, whose SITES refuse this
                                  client and whose own GIS layers carry the
                                  roster as feature attributes;
  * ARCHIVE_COUNTIES            - Fond du Lac, whose host denies this client and
                                  whose public page the Internet Archive holds;
                                  the county is still asked FIRST every run and
                                  the copy's age is gated before any name is used;
  * CONSTITUENT_COUNTIES        - Dodge, whose 33 seats sit in a paginated
                                  constituent directory needing its own fetch;
  * WITNESSED_DOCUMENT_COUNTIES - Kenosha, whose Clerk publishes the roster in a
                                  directory PDF this file FETCHES and cross-checks
                                  against the board's own page every run;
  * PDF_COUNTIES                - Adams, whose directory PDF is fetchable and
                                  district-keyed, so it is re-read weekly like a page;
  * CLARK_DIRECTORY             - Clark, whose board page names only the chair
                                  and whose Clerk's 44-page OFFICIAL DIRECTORY
                                  prints all 29 seats eleven pages further in,
                                  each with the ward composition that witnesses
                                  the numbering. The link is discovered by its
                                  anchor TEXT because the county is on Wix and
                                  serves the file from a content hash;
  * PIERCE_DIRECTORY            - Pierce, whose annual county directory prints
                                  all 17 seats in TWO COLUMNS (composition left,
                                  home address right, so the columns are split
                                  by x-position and the addresses dropped), each
                                  with a firstname.lastname county mailbox that
                                  witnesses the name and a sideways summary index
                                  that witnesses every seat a second time. Its
                                  URL is PINNED, not discovered, because the
                                  host's robots.txt allows documents and forbids
                                  pages — the county's own site redirects there;
  * `pdf-roster`                - Jackson, whose HTML names nobody anywhere and
                                  whose own listing page links a district-keyed
                                  roster PDF, DISCOVERED fresh each run because
                                  its filename carries the board's term;
  * `directory`                 - Waupaca, whose BOARD page names nobody and
                                  whose Clerk publishes a district-keyed
                                  Directory of Public Officials as a live page
                                  on the county's own host;
  * `staff-directory`           - Door, whose board page gives every district a
                                  CivicPlus staff-directory widget stating the
                                  district THREE ways — header, job title and
                                  county mailbox — gated on all three agreeing;
  * `member-cards`              - Oconto, whose 31 members sit in ONE such
                                  widget, alphabetical by surname, the district
                                  stated only inside each card's job title and
                                  the phones on each member's own page;
  * FRAMED_TABLE_COUNTIES       - Columbia, whose listing page is a shell around
                                  an iframe onto a second county host;
  * DOCUMENT_ROSTERS            - NINE counties, in two classes. Taylor,
                                  Lafayette and La Crosse are BLOCKED: their
                                  hosts answer a captcha or a Cloudflare
                                  challenge, and Lafayette re-tries its live
                                  page each run because it PARSES the moment
                                  the challenge lifts. Pepin, Jackson,
                                  Richland, Rusk, Polk and Dunn are the
                                  OPPOSITE case — every one of those sites
                                  answers this client perfectly well and every
                                  one publishes a robots.txt disallowing the
                                  whole site to every agent it does not name.
                                  None of the six carries a `live` key, by
                                  design: a re-try is a fetch. See the header
                                  of that table and validate_robots.py.

The last two are not the same arrangement and the difference is stated where
each is defined: a WITNESSED document is fetched and checked every week; a
CARRIED one was read once, by a person, through an access control this file does
not try to defeat.

WHY ONLY FIFTY-SEVEN OF SEVENTY-TWO
-----------------------------------
Wisconsin publishes county board DISTRICTS statewide (Wis. Stat. 5.15(4)(br)1,
see build_wi_supervisory_districts.py) and publishes the PEOPLE in them nowhere:
each county names its own supervisors, 72 different ways. Fifty-seven are
reachable by one of the routes above. The other 15 are not oversights and are
recorded as such — and the record is worth reading before adding to it, because on
2026-08-29 seventeen counties joined at once and ALMOST NONE OF THEM HAD STARTED
PUBLISHING ANYTHING NEW. What changed was this file:

  * MARATHON answers 200 with the header set an ordinary Chrome navigation
    sends, and is unread here only for want of a pinned reading. It is the last
    of the four counties that measurement freed (Outagamie, Rock and Sheboygan
    were the others, and all three now ship).
  * LINCOLN answers a Cloudflare managed challenge on every path and header
    tried. A challenge is an access control and is not defeated here.
  * FOREST does not resolve at all.
  * THE MAP-ONLY BULLET IS NOW EMPTY, and its last occupant is the reason to
    distrust the whole list. It read "OCONTO publishes district MAPS — a page
    per district with a PDF and no name on it anywhere, re-checked 2026-08-29
    and the record held", and it was an accurate description of
    /307/County-Board-Supervisory-District-Maps. Oconto's ROSTER is at
    /453/County-Board and names all 31 members; the county was in this bullet
    for a year with the answer one slug away, exactly as Kenosha and Ozaukee had
    been until 2026-08-29. Three counties, one mistake, three times. RE-CHECKING
    A RECORD IS NOT RE-CHECKING THE COUNTY — the 2026-08-29 pass confirmed what
    the map page says and never asked whether it was the right page.
  * PEPIN IS THE ONE COUNTY HERE HELD BACK BY A ROBOTS.TXT, and it is not in
    any bucket above because none of them describes it. Its site answers this
    client perfectly well and publishes all 12 districts with a phone each and
    ten county mailboxes; its robots.txt names six search-engine agents, gives
    each a narrow Disallow, and then tells everything else `Disallow: /`. THAT
    IS THE EXACT OPPOSITE OF IOWA AND WAUSHARA, whose files this scraper reads
    precisely because their `*` group PERMITS the board path. A county that
    asks not to be crawled has not refused to publish, so Pepin's roster is
    transcribed by a person and carried in DOCUMENT_ROSTERS with no automated
    re-read — and the card says the county ASKED rather than the default
    sentence's "refuses", because those are different facts.
  * The remaining 13 publish their members as images or prose with no district
    column on the pages their own sites point to. THAT NUMBER WENT 18 -> 13 ON
    2026-08-31 AND NONE OF THE FIVE THAT LEFT EVER BELONGED IN IT. Calumet
    publishes all 21 supervisors district-keyed with a phone each; Buffalo all
    14 with a county e-mail for 12; Jackson all 19 with both; Waupaca all 27
    with both; Door all 21 with both, a per-supervisor page each, and the
    district stated THREE ways per block. Nobody had opened any of the five
    pages. The bullet said "THE 53RD IS IN THIS BULLET" and it was, three times
    over — re-reading the list is what produced every one of them.
    TWO OF THE FIVE SHARPEN THE BULLET'S OWN WORDING, and it is now the
    sentence to distrust. "Publishes no district column ON THE PAGES THEIR OWN
    SITES POINT TO" is true of Jackson's HTML and of Waupaca's board page, and
    false of both counties: Jackson's site names no supervisor anywhere and
    links a PDF naming all 19; Waupaca's /county_board/ carries four paragraphs
    about what a county board is, with ZERO "District n" on it, while the
    county's home page links the Clerk's Directory of Public Officials naming
    all 27. A COUNTY'S HTML IS NOT THE COUNTY, AND ITS BOARD PAGE IS NOT ITS
    CLERK. Ask what a county's pages LINK before recording what they say.
    DOOR IS THE PLAINEST OF THE FIVE AND THEREFORE THE MOST DAMNING: its board
    page needs no link followed and no document opened — it names all 21
    supervisors in the county's own staff directory, with a mailbox, a phone
    and a page each, and it always did.

SEVEN WAYS THAT LIST HAS BEEN WRONG, EACH FOUND BY CHECKING RATHER THAN GUESSING
--------------------------------------------------------------------------------
  1. A 403 MEASURES THE REQUEST, NOT THE COUNTY. The bucket used to say nine
     counties answer 403 "and hold it against browser headers", where browser
     headers meant the three this file sent: a User-Agent, an Accept and an
     Accept-Language. Monroe's Akamai bot management scores the WHOLE request:
     those three are refused from any User-Agent, and so is UA plus all four
     Sec-Fetch-* headers, while UA + Accept + Accept-Language + Sec-Fetch-*
     together — what an ordinary Chrome navigation sends — is served the full
     153 KB page from this same datacenter address. Five of the nine were wrong.
     And Outagamie is the OPPOSITE case: its edge denies any `Mozilla/`-prefixed
     user-agent and serves a client that says honestly what it is, which is the
     one county where the browser string WAS the block. Outagamie's answer
     generalised on 2026-09-12: asked with the token, 67 of the 74 hosts this
     file fetches serve it a full page, so the token is now the default and the
     six that refuse it are pinned in TOKEN_REFUSED_HOSTS — per host, never
     negotiated, so a weekly run sends identical bytes and the log says which
     request worked.
  2. A PDF IS A FORMAT, NOT A BLOCKER. "Publishes a PDF" sat in the unreadable
     bucket until Adams, and the disqualifier was always "no district column".
     The question is whether the document carries a TEXT LAYER and a district
     beside each name. Adams's does, and had for as long as this file existed.
     OPEN THE FILE BEFORE FILING THE COUNTY. Adams then looks like Taylor and is
     not: nothing blocks Adams, so Adams SCRAPES where Taylor is CARRIED. Sort a
     county by what the client can reach, never by what the source is made of.
  3. A LISTING PAGE THAT READS AS EMPTY MAY BE FRAMING THE ANSWER. Columbia
     publishes all 28 seats with a profile page per supervisor and its chair and
     both vice chairs named — a fuller list than most counties already shipping —
     and this scraper could not see one character, because the page is a shell
     around an <iframe> onto a second host with the name split across a First
     Name cell and a Last Name cell. "The page carries no name" and "the county
     publishes no name" are different measurements.
  4. CHECK WHICH BOARD PAGE. Kenosha's record described
     /142/County-Board-Supervisor-Districts — an index of 23 links to 23 PDF
     maps with nobody's name on it — accurately, and that is not the county's
     roster page. /113/County-Board-of-Supervisors is, and it names all 23. Two
     slugs one word apart, one a map index and one the answer.
  5. READ THE BODY, NOT THE STATUS CODE. Dodge was filed under "publishes
     prose"; co.dodge.wi.us had become a 261-byte "This site has permanently
     moved" stub answering HTTP 200, and the county is at www.co.dodge.wi.gov
     publishing all 33 seats district-keyed. A sweep that reads a status code
     cannot tell a county that publishes nothing from a county that left a
     forwarding note. See build_wi_county_board_directory.py --probe.
  6. A COUNTY'S OWN PAGE CAN CONTRADICT ITSELF, AND THE COUNT GUARDS CANNOT SEE
     IT. Calumet (2026-08-31) names all 21 supervisors correctly and gives TWO
     of them the same role: districts 4 and 19 are both "Vice-Chairperson", and
     the county's organisational minutes of 21 April 2026 show district 19's is
     a label from the previous term. Every guard in this file counts SEATS —
     all of them, each once — and 21 correct names carrying one wrong role pass
     every one. So a field that is not the seat itself needs its own gate: the
     roles here ship only where exactly one supervisor claims them. THE THING
     WORTH TAKING TO THE NEXT COUNTY is that the contradiction was visible only
     because the page states the role in the first place; a county that names
     its chair somewhere else can be stale with nothing to compare against.
  7. THE SAME BLIND SPOT, ONE LEVEL DOWN: A ROLE THAT DOES NOT MATCH ITS REGEX
     IS INVISIBLE. Buffalo (2026-08-31) resolved 14 of 14 seats on its first run
     with its CHAIRMAN unnamed, and every guard stayed green. The role pattern
     read `chair(?:man|person|woman)`, which requires a suffix: true of
     Calumet's "Chairperson" a day earlier, false of Buffalo's bare "Chair". The
     county published the role, the reader saw the line, and the regex declined
     it silently. Finding 6 says a field that is not the seat needs its own
     gate; this is the same sentence about the field's own PARSER, and it was
     caught only by reading the fourteen rows against the page. WHEN A NEW
     COUNTY SHARES A PATTERN WITH AN OLD ONE, RE-READ THE OUTPUT ROW BY ROW —
     the count is the one thing that cannot tell you.

MARINETTE IS THE ONE INFERENCE THIS FILE MAKES, and it is opt-in per county:
the board page numbers 29 of 30 seats and prints one unnumbered "VACANT SEAT"
row, so district 26 is assigned by elimination — gated on arithmetic re-checked
every run (EXACTLY one district unclaimed AND EXACTLY one unnumbered vacancy
line), never a general rule. See ELIMINATION_VACANCY.

OZAUKEE WAS NEVER A MAP-ONLY COUNTY (2026-08-29)
-------------------------------------------------
Ozaukee was named in the map-index bullet above for four days — it is not
there now — as one of the counties that publish "district MAPS ... and no name
on it anywhere", checked "three pages deep". It
publishes all twenty-six supervisors in one district-keyed HTML TABLE at
ozaukeecounty.gov/701/County-Board — District Map / Name / Address / Phone /
Email, one row per seat — and it ships from that page under the ordinary
`column-after` reading, with no new code.

WHAT WENT WRONG IS THE SAME THING THAT WENT WRONG WITH DANE, ONE LEVEL DOWN.
Dane's lesson was recorded as "ask the BOARD's own HOST": its roster is on
board.danecounty.gov rather than the county domain. Ozaukee is on the county's
own host, so that rule reported nothing wrong — the miss is that the URL this
project already held for Ozaukee, in build_wi_county_board_directory.py, is
/2206/Supervisory-District-Maps. THAT PAGE IS EXACTLY WHAT THE OLD RECORD
DESCRIBES: a map index, a PDF per district, no person on it. The county's
BOARD page is a different page on the same host, and the sweep that wrote the
record never reached it. So the rule generalises past the host: ASK THE
BOARD'S OWN PAGE. A county filed under "publishes maps" is a county whose MAP
page was read, which is not evidence about its board page.

Whether the table was also there when the record was written could not be
established from here: web.archive.org holds a snapshot of /701/County-Board
from 2025-09-28, and this sandbox's egress policy blocks that host (the
availability API on archive.org answers; the snapshot itself does not). So
this entry does NOT claim the old check was careless — only that the page it
describes is the maps page, and that the board page reads cleanly today.

KENOSHA AND OCONTO WERE RE-CHECKED THE SAME DAY AND BOTH RECORDS HELD, which
is what bounds the correction to one county. Oconto's board page is a pure
index of 31 district PDFs with no person on it. Kenosha's own board pages link
"Who is my County Board Supervisor?", which sounds like the missing roster and
is a POINTER TO A LOOKUP TOOL ("Where Do I Vote and Who are My
Representatives?") carrying no roster of its own. Neither county yields a
single name-shaped line outside site navigation under any of the five
readings. They stay out on measurement, not on inheritance.

FOUR TRAPS ON OZAUKEE'S PAGE, THREE OF WHICH WOULD SHIP SILENTLY
----------------------------------------------------------------
  * A STRAY EMPTY <table> IS NESTED IN DISTRICT 9's PHONE CELL
    (`<table class="style4" id="table20"></table>262-377-7650`, CMS editor
    debris). A non-greedy `<table>.*?</table>` match therefore closes the
    outer table on the INNER one's tag and returns EIGHT rows of twenty-six —
    a clean-looking parse that drops two thirds of the board. `to_lines`
    strips tags rather than parsing the table, so this scraper never sees it;
    it is recorded because reaching for the row structure (to pick up the
    phone or e-mail columns) walks straight into it, and because eight
    plausible rows is precisely the partial output the all-seats-or-nothing
    rule exists to refuse.

  * THE ADDRESS COLUMN READS AS A NAME. "Belgium, WI" passes `is_name`, and
    `clean` flips it on the comma to "WI Belgium". Under `column-before` the
    page resolves 25 of 26 seats, reports NO vacancy, and fills the roster
    with mangled place names — a full, confident, entirely wrong answer, and a
    live demonstration of why the reading direction is PINNED per county
    rather than detected. `column-after` reaches the Name cell first and never
    sees the address.

  * THE E-MAIL COLUMN NAMES THE WRONG PEOPLE. Most rows link a CivicPlus
    contact FORM rather than an address, and the form slugs were not renamed
    when seats changed hands: District 3 (Marcia Nosko) links
    Email-Supervisor-Barbara-Jobs-223 and District 5 (Scott R. Fischer) links
    Email-Supervisor-Donald-Clark-225. A slug is not a name source.

  * SOME ROWS CARRY HIDDEN mailto: LINKS WITH EMPTY ANCHOR TEXT — invisible to
    a reader of the page, and a mixture of county addresses, private ones
    (gmail/aol/att.net), and at least one PREDECESSOR's: District 7's row
    holds Tony Matera's own tmatera@co.ozaukee.wi.us AND
    dbecker@x-celtooling.com, a private business address for someone not in
    office. No rule picks the right one — "prefer the county domain" works for
    District 7 and fails District 6 and 8, which carry only private
    addresses — so NO E-MAIL SHIPS FOR OZAUKEE. The county's own contact
    surface is the board page, which the card already links.

  Phone is not carried either, and for a plainer reason: five of the
  twenty-six rows print 262-284-9411, which is the county's MAIN SWITCHBOARD
  (it is the number in the site footer), so the column is not a per-supervisor
  fact. The card renders neither field today in any case.

WHAT WITNESSES THE OZAUKEE ROSTER
----------------------------------
Every one of the 25 named seats was confirmed against a SECOND county surface
on 2026-08-29: each row's Name cell links that supervisor's own profile page,
and all 25 state their district in their own text (District 1 Bichler ...
District 26 Foy) and repeat the member's surname — so a row shift of the kind
`column-before` produces would have been caught by 25 disagreements rather
than by eye. District 21, which the table marks Vacant, is the ONLY row with
no profile link, corroborating the vacancy independently of the word. Those
pages are a verification run by hand, not a weekly fetch: the shipped source
stays the one board page, and the builder's existing gate against the LTSB
geometry (26 districts, numbered 1..26) is what re-checks the shape each week.
    ITS CONTENTS CAME FROM THE OPERATOR'S OWN BROWSER (2026-08-29). The
    first read covered districts 1-12 of 17 and the all-seats-or-nothing
    rule held Taylor back until 13-17 arrived; all seventeen ship now, from
    DOCUMENT_ROSTERS below.

    LA CROSSE IS THE SAME FINDING BEHIND A DIFFERENT DOOR (2026-08-29), and
    it is why the 403 bucket above is worth re-testing county by county
    rather than believed. lacrossecounty.org/countyboard/members publishes
    all thirty districts, each with a name, a phone, a photo, committee
    assignments and a biography, and marks its board officers — the richest
    county board page in the fleet. Nothing here can read it: Cloudflare
    answers 403 ("Sorry, you have been blocked") to every path on the host,
    gis.lacrossecounty.org included, and it holds from two independent
    networks, so this is the site's own bot rule rather than one client's
    address. THAT IS A DIFFERENT CLOUDFLARE PRODUCT FROM THE ONE THE GAP
    RECORD ASSUMED: Lafayette and Lincoln serve "Just a moment..." (5,561
    and 5,556 bytes), an interactive challenge a real browser might pass,
    where La Crosse serves "Attention Required! | Cloudflare" at 5,492
    bytes. Seventy bytes apart, and only one of them leaves a route open.

    Every other route was measured shut before the document was asked for,
    and each is worth stating so nobody re-walks it:

      * the county's ArcGIS Online org (services.arcgis.com/YTojcvpJ9GpgYxjF)
        answers fine and carries 174 public services — the Douglas move of
        asking the ORG rather than the viewer. Its Supervisor Districts layer
        has thirty features and no supervisor on any of them; the county's
        people are simply not in its GIS.
      * lacrossecounty.legistar.com resolves and its Web API answers
        "LegistarConnectionString setting is not set up in InSite for client:
        lacrossecounty" — a tenant that was never provisioned, not a portal
        that is merely empty.
      * no second county domain exists (co.la-crosse.wi.us, lacrossecounty.gov
        and six more do not resolve), and no election-results vendor carries
        the county.
      * THE ARCHIVE HAS THE PAGE AND IT CANNOT BE USED. Its last capture of
        /countyboard/members is 2025-10-11, which is the 2024-2026 board, and
        Wisconsin reseats every county board at the April election of each
        even year. The seat this file can still demonstrate moved is district
        4, Freedland -> Kathy Allen, which is what the county's own current
        page names. A stale roster reads exactly like a current one, which is
        the whole reason to say no to it.

        CORRECTED 2026-08-29: this bullet also offered "district 6 Mathu ->
        Rauschnot" as a second demonstration, and it is contradicted by the
        very document this county ships from — the page read that day names
        GRANT MATHU in district 6, and so does the roster below. Whichever way
        round the archived capture had it, the example cannot be doing the work
        it was written to do, so it is struck rather than reversed: the archive
        was unreachable from this project's network when the correction was
        made (web.archive.org resets the connection), and asserting the
        opposite direction would be swapping one unchecked claim for another.
        A RECORD'S OWN EXAMPLES ARE CLAIMS AND HAVE TO SURVIVE THE SAME CHECK
        AS THE DATA — this one contradicted the roster shipping beside it and
        no gate compares the two.

    So La Crosse rides DOCUMENT_ROSTERS on Taylor's route, with the same
    dated NOT RE-READ line every run.

    TWO OF ITS FIVE TITLE LINES ARE NOT BOARD OFFICES. The page prints a
    title under five supervisors' names: "1st Vice Chair" (district 3),
    "2nd Vice Chair" (district 10), "Chair, Executive" (13), "Chair,
    Planning, Resources & Development" (29) and "Chair, Health & Human
    Services" (30). Only the first three are board officers; the last two
    are COMMITTEE chairs, and a title-keyed read ships three chairs for a
    board that has one. The discriminator is the comma: "Chair, <committee>"
    where the committee is a standing committee. District 13 reads that way
    too and is the real one — the board chair chairs the Executive Committee
    ex officio, her own biography says "I'm honored and humbled to serve as
    County Board Chair", and the Blue Book (April 2025) independently names
    Tina Tryggestad as La Crosse's chair. Which is why `roles` below is a
    SEPARATE map from `members`: the transcription of the page and the
    judgement about what a title means are different acts, and only the
    second one can be wrong. `document_county` refuses more than one chair.

    NO E-MAIL ADDRESS SHIPS FOR LA CROSSE and that is the page, not the
    read: it renders each supervisor's address as a bare "Email" link with
    no address in the text, the same shape as Brown County's obfuscated
    mailtos. Phones are carried verbatim, in the county's own inconsistent
    formatting. STREET ADDRESSES ARE NOT CARRIED — the page prints a home
    address for every supervisor, and a supervisor's house is not an office
    location (the rule Taylor set).
  * The rest could not be read: Lincoln answers 403, and the remainder
    publish their members as PDFs, images or prose with no district column —
    but see the next section before trusting that list, because eight of the
    nine counties it used to hold turned out to answer.

WHAT THE HEADER FIX RETIRED (2026-08-29)
----------------------------------------
A bucket of NINE counties sat here under the sentence "answer 403 to a
datacenter client and hold it against browser headers", and that sentence was
wrong about the headers, not about the counties. See the UA dict below for the
measurement. Re-probed with the corrected client, EIGHT OF THE NINE ANSWER:
Sheboygan (which ships here), Marathon, Outagamie, Fond du Lac, Monroe and
Rock consistently, La Crosse and Lafayette intermittently. Only LINCOLN still
refuses.

THE OTHER SEVEN ARE NOT IN THE TABLE, and this is what was measured of each on
2026-08-29 so the next pass reads a measurement rather than re-deriving one:

  * ROCK (/government/county-board-of-supervisors) resolves 29 of 29 seats
    under `before`, `after` AND both strict readings. That is exactly the
    ambiguity this file pins directions to avoid, so Rock's direction has to
    come from READING the page — never from whichever reading resolves.
  * FOND DU LAC (/government/county-board-supervisors on the WWW host)
    resolves 20 of 25 as `same-line`. Partial is not shippable, so the five it
    misses are the question.
  * MONROE (/government/county-board-of-supervisors/districts-supervisors) is
    a COLUMN page: 13 of 16 forward, 15 of 16 backward. Neither is complete.
  * MARATHON and OUTAGAMIE answer, and the board pages their own front pages
    link yield no district-keyed reading at all — each needs its member list
    LOCATED before anything can be said about its shape.
  * LA CROSSE and LAFAYETTE answered one probe and refused the next within the
    same hour. That is the class Outagamie was already recorded under, and a
    roster this client cannot re-verify weekly does not ship.

Fond du Lac carries one more measurement worth keeping: the county-board
DIRECTORY had it at `http://fdlco.wi.gov/`, which answers 200 with a default
"IIS Windows Server" placeholder — 703 bytes, no county content. The county is
on the WWW host over HTTPS. A 200 is not a page.

TAYLOR: A CAPTCHA HIDING A DIRECTORY
------------------------------------
Taylor was filed under "publishes nothing readable" only because nothing here
can SEE the page. It publishes a County Board directory at
co.taylor.wi.us/directory/county-board/ that is district-keyed and carries a
name, a county e-mail, a street address and a phone per supervisor — richer
than most of the counties that do ship. The block is the host, not the county:
every path on co.taylor.wi.us answers HTTP 202 with a 196-byte meta-refresh to
`/.well-known/sgcaptcha/` and an `sg-captcha: challenge` header, and the three
other Taylor hosts tried (taylorcountywi.gov, its www, and gis.co.taylor.wi.us)
do not resolve at all. A captcha is an access control and is not defeated here,
so NO WEEKLY SCRAPE OF TAYLOR IS POSSIBLE: its seventeen seats ride
DOCUMENT_ROSTERS below, read from that page in an ordinary browser by the
operator, printing a dated NOT RE-READ line every run (the Edwards/Wabash
pattern in Illinois's il_county_commissioners_scraper.py) — never this table.

The first paste covered districts 1-12 of 17 and the all-seats-or-nothing rule
held the county back until 13-17 arrived: 12 of 17 would have read as a
complete board with five empty seats.

NINE OF THOSE "UNREADABLE" COUNTIES WERE PUBLISHING ALL ALONG (2026-08-27)
--------------------------------------------------------------------------
Dane 37, Shawano 27, Juneau 21, Oneida 21, Richland 21, Kewaunee 20, Rusk 19,
Trempealeau 17 and Price 13 — 196 seats — were recorded here as publishing
nothing readable, and both causes were on this side of the wire.

The re-sweep was provoked by one county: build_wi_supervisory_districts.py's
docstring cites Trempealeau's own board page as the authority for its
seventeen seats, that page was never wired into this scraper, and a cold-ask
e-mail was being drafted to the county for a list it publishes.

  CAUSE ONE, THE READER. `DIST` needs the literal word "district" beside the
  number. A page that says it once in a COLUMN HEADER and then prints bare
  numerals in the cells is invisible to all three original readings — so
  Oneida, Price and Trempealeau were filed under "no district column" when
  having one is exactly why they could not be read. `_column` reads the cell.

  CAUSE TWO, THE SWEEP. It asked each COUNTY's site and never the BOARD's.
  Dane's 37 supervisors are on board.danecounty.gov, a different host from the
  countyofdane.com this project's own clerk file carries. ASK THE BOARD'S OWN
  HOST BEFORE RECORDING THAT A COUNTY PUBLISHES NOTHING.

IOWA COUNTY: THE PAGE ITS OWN HOME PAGE LINKS NO PATH TO (2026-08-29)
---------------------------------------------------------------------
Iowa was in the "publishes no district-keyed list on the pages their own sites
point to" bucket, and that sentence was exactly true and still described this
side of the wire. The county publishes all 21 districts at
/departments/countyboard/county-board-members with a name, a per-district county
e-mail alias and a phone on each — as rich as any page in this table — and
www.iowacountywi.gov's home page carries NOT ONE anchor whose href contains
"board", because its DEPARTMENTS menu is built by script. A harvest of a county
home page's own links therefore finds no route to it at all, and the page sits
two hops in behind a menu that only a browser assembles.

That is the Dane lesson one turn further on. Dane said ask the BOARD's host as
well as the county's; Iowa says a county's own site can HAVE the page and link
it from nowhere a link harvest can see. Neither county was withholding
anything.

READ THE SITEMAP. It is the route that would have found this one and costs a
single request: www.iowacountywi.gov/sitemap.xml lists 3,173 pages, and
`/county-board-members` — a flat alias of the same page, serving the same 21
supervisors — is one of them. A site whose menu is script-built still has to
tell search engines what it publishes. (Its robots.txt allows this path to a
general crawler: the `User-agent: *` block disallows only /calendar, /meetings,
/media, /portal and a few others, and asks a crawl-delay of 5 seconds, which a
weekly one-page fetch of this host meets by construction.)

WHAT IS NOT CARRIED, AND WHY. The page prints three things per supervisor this
table does not ship. The street addresses are supervisors' HOMES ("6067 Helena
Rd."), and a home address never ships here even when the source publishes it —
the same rule Taylor's document rides. The phone and the county e-mail alias
(supervisor14@iowacounty.org, on the county's older domain) are official
contact details and are simply not read: the county-board card renders a
supervisor's name and nothing else, so the two GIS counties' e-mails already
sit in the shipped file unread, and a new per-county contact reading with no
reader is risk for nothing. If that card ever grows a contact line, Iowa's
addresses are self-verifying — the number IN the alias must equal the district
it is filed under — and this paragraph is the note saying where to start.

Iowa marks no chair and no vacancy, which matters to the officer builder rather
than to this one: the Blue Book's Iowa chair, John M Meyers, sits at district
14, so its weekly reconciliation CONFIRMS the dated book row instead of
withholding it.
KENOSHA'S OWN CLERK PUBLISHES MORE THAN ITS BOARD PAGE DOES (2026-08-29)
------------------------------------------------------------------------
Its own miss is recorded in the bucket list above — the wrong board page. What
it adds to this file is the route: the county's Clerk publishes MORE than the
board page does, in a DOCUMENT rather than on a page. The annual Directory of
Public Officials (a 107-page PDF) prints the same 23 districts with a PHONE and
an E-MAIL each, and marks the Chair and Vice-Chair on their own rows. No other
county here publishes contact for its board at all.

TWO KINDS OF DOCUMENT LIVE IN THIS FILE NOW AND THEY ARE OPPOSITES. Taylor's
roster is CARRIED (DOCUMENT_ROSTERS): read once by an operator in a browser
because a captcha fronts every automated client, never re-read by a run, and
the output SAYS SO on every record. Kenosha's is WITNESSED
(WITNESSED_DOCUMENT_COUNTIES): fetched fresh every run, cross-checked against
the county's own board page name-for-name, and no more stale than any page
county here. A record carrying `carried_from_document` is the first kind; the
absence of that flag is the second. Do not merge the two strategies because
both say "document" — the flag is a currency claim a reader sees.

THE STABLE URL IS A COUNTY PAGE ID, NEVER THE DOCUMENT'S OWN ADDRESS. The PDF
lives at /DocumentCenter/View/<edition>/County-Directory, and <edition> changes
with each year's directory — that URL freezes on the 2026-2027 edition and
would go on being fetched, successfully, forever. /1018/County-Directory-PDF is
the county's own page for "the current directory" and 302s to whichever edition
is live, so the run log prints the edition it landed on and an edition change is
visible instead of silent.
CRAWFORD'S "PUBLISHES NOTHING" RECORD WAS OURS (2026-08-29)
-----------------------------------------------------------
Crawford was one of ten counties the 2026-08-27 re-sweep left in the bucket
"publish no district-keyed list on the pages their own sites point to". Its own
site points at one: www.crawfordcountywi.gov/boardsupervisors carries all
seventeen districts, each as a "District N - <the wards it covers>" heading
followed by "Supervisor", the supervisor's name, a phone, and a street address.
Seventeen of seventeen resolve under both the plain and the strict `after`
readings, and they name the same people.

WHAT THE SWEEP COULD HAVE MISSED IT ON is measurable and worth pinning: the
county's front page links that page ONCE, and the anchor text is the word
"Government". Only the HREF says board. A link harvest scored on link TEXT
never sees it; one scored on the URL does. Which of the two the sweep did is
not recorded here, so the durable rule is to score BOTH — and the previous
domain lesson does not apply, since the clerk association's crawfordcountywi.ORG
redirects to the .gov and serves the same page.

THE PHONE AND THE ADDRESS ARE NOT CARRIED. The address is the supervisor's
home ("53201 Kuhn Drive"), and a home address never ships here even when the
source publishes it — the Taylor rule. The phone would ship under that same
rule, and does not for a different reason: nothing in the page-scraped path
carries contact at all (the builder ships `email`/`profileUrl` only where a
county GIS feature or the Taylor document supplied them), so a phone-only
Crawford row would be the first of its kind and the card has no contact row to
render it in. It is left in the county's page rather than in this file.
OUTAGAMIE: THE BROWSER USER-AGENT WAS THE BLOCK (2026-08-29)
-----------------------------------------------------------
Outagamie's 36 seats were recorded in the 403 bucket above, and the note by
ARCGIS_COUNTIES said its site "answered one probe on 2026-08-25 and refused
every later one (HTTP 403 across UAs)". Both halves were measured; the
conclusion drawn from them was wrong, because "across UAs" meant across
BROWSER UAs, and this scraper only ever sends one of those.

www.outagamie.gov is fronted by Akamai (`Server-Timing: ak_p`, an
errors.edgesuite.net reference in the deny body) with a rule that refuses any
client CLAIMING to be a browser it cannot fingerprint as one. Measured the
same minute, same host, same path:

    User-Agent: Mozilla/5.0 (... Chrome/124.0 ...)   -> HTTP 403 Access Denied
    User-Agent: Mozilla/5.0 (... Firefox/127.0)      -> HTTP 403 Access Denied
    User-Agent: Mozilla/5.0 (... Safari/605.1.15)    -> HTTP 403 Access Denied
    User-Agent: Mozilla/5.0                          -> HTTP 403 Access Denied
    User-Agent: Mozilla/5.0 (compatible; Googlebot/2.1; ...) -> HTTP 403
    User-Agent: curl/8.5.0                           -> HTTP 200, full roster
    User-Agent: Python-urllib/3.11                   -> HTTP 200, full roster
    no User-Agent at all                             -> HTTP 200, full roster

Every denial is a `Mozilla/`-prefixed string and every success is an honest
one; the three passing shapes return byte-comparable pages (36 districts, 36
county e-mail addresses). The one 2026-08-25 probe that DID answer will have
been a default-UA request, and every "later one" a spoofed-browser retry —
which is exactly the pattern the record preserved without reading it.

SO THE SPOOFED CHROME STRING IN `UA` WAS ITSELF THE CAUSE, and a UA meant to
look ordinary is not a neutral default: on a bot-managed edge it is the single
most suspicious thing a datacenter client can say. Outagamie was pinned to an
honest client string for two weeks while every other county kept the spoofed
one; on 2026-09-12 the whole host list was asked with the token and 67 of 74
served it, so the pin became the default and TOKEN_REFUSED_HOSTS carries the
six exceptions — per HOST, because the rule belongs to the edge and not to the
county's page shape, and pinned rather than detected so a weekly run sends the
same bytes every week.

THE FINDING IS BOUNDED, and was tested rather than generalised: all eight
counties left in that bucket were re-probed with both UAs on 2026-08-29, and
seven of them (Marathon, La Crosse, Lafayette, Lincoln, Monroe, Rock,
Sheboygan) answer 403 to BOTH, so their blocks are real and stay recorded. The
eighth, Fond du Lac, answers 200 to both and is a different question — its
front door serves a 703-byte shell, which is why its board was never read from
it. ONE COUNTY MOVED; THE BUCKET WAS NOT WRONG ABOUT THE REST.

THE READING DIRECTION IS PINNED PER COUNTY, NOT DETECTED
--------------------------------------------------------
Three page shapes carry the same information:

    same-line   "District #1 - Steve Sandstrom"      (Bayfield)
    before      "Jim Brown" then ": District 1"      (Green)
    after       "District 1" then "Tim Lauffer"      (Dunn)

`before` and `after` are the SAME EXTRACTION SHIFTED BY ONE, so a page read in
the wrong direction yields a full, plausible, entirely wrong roster: every
supervisor filed under their neighbour's district. Green County resolves 31 of
31 under both readings and they name different people. Detecting the direction
at runtime would mean a page tweak could silently flip it, so each county's
direction is PINNED here and a mismatch fails the county's count guard loudly
instead.

Two more shapes joined in the 2026-08-27 re-sweep, and both are pinned the
same way:

    column      a District COLUMN of bare numerals (Oneida, Price,
                Trempealeau) — see `_column`
    -strict     as before/after, but the scan STOPS at the next district line
                (Crawford, Richland, Rusk, Shawano) — see `_windowed_strict`

A fifth joined on 2026-08-29 with Lafayette:

    same-line-lead
                the name FIRST and the district LAST, the office between them
                ("Larry Ludlum- Supervisor District #1") — see
                `_same_line_lead`. It is the only reading that recovers a ROLE
                from the seat's own row, because it is the only one that reads
                the words between the person and the district. It is pinned on
                a DOCUMENT_ROSTERS entry rather than in COUNTIES, because the
                host refuses this client; the run tries it anyway, every time.

A fifth joined 2026-08-29 and is NOT a direction at all:

    indexroll   one self-contained BLOCK per person, so a field belongs to a
                supervisor by CONTAINMENT rather than by proximity (Green
                Lake) — see `_indexroll`

That is the shape to look for first. A direction has to be pinned because a
window can cross into a neighbour's row; a block cannot, and it is the only
shape that carries the role, e-mail and phone that sit at no fixed distance
from the district number.

A FIFTH SHAPE HAS NO DIRECTION TO PIN AT ALL (Sauk, 2026-08-29):

    fielded     the page LABELS its own fields — "Supervisor: Schroder,
                Palmer" — so the name is not near a district, it is in a
                field the page names; see `_fielded`

That is the whole point of it. `before` and `after` are one extraction shifted
by one BECAUSE adjacency is all those pages give; a labelled field cannot be
read off by one, and a page tweak cannot silently flip it. Sauk resolves all
thirty-one seats where every windowed reading resolves ZERO — `is_name` rejects
its "Supervisor: ..." line on the word supervisor and its ward lines on
town/city/village/ward, so the county sat in the bucket below reading as though
it published nothing. It publishes more than most: a name, a county e-mail, a
phone and the district's ward composition per seat. THE READER WAS THE BLOCK
FOR A THIRD TIME (nine counties on 2026-08-27, Taylor's host on 2026-08-29,
this reader now) — and the fielded shape brings its own witnesses with it,
which the FIELDED_PINS comment sets out: the e-mail on each row checks that
row's own name, and the ward composition checks the county's district NUMBERING
against LTSB's, the one thing no other county in this file can prove.

A sixth joined on 2026-08-29 with Manitowoc, and it is the one shape none of
the five could see:

    numbered-line   "1        Lillibridge, James"   — see `_numbered_line`

The number and the name are on ONE line, and the word "district" is nowhere
near them: Manitowoc says it once in a column header ("District Number Name")
and then prints bare numerals beside the names. That is `_column`'s page
written on one line instead of two, so `DIST` cannot see it (no word) and
`BARE_NUM` cannot either (the cell is not a lone numeral). Requiring BOTH
halves — a leading 1-2 digit number AND a remainder that reads as a name — is
what makes a bare-number reading safe here, and it is why this is its own
strategy rather than a loosening of `_column`.

THE OFFICERS BLOCK IS PINNED THE SAME WAY, and for the same reason one page
later: `attach_officer_roles` DETECTS its direction and refuses when both
neighbours read as names, which is right for a page with one officer and blind
to an alternating "name / role / name / role" run — Sheboygan's chair sits
between two names and was silently dropped while its vice chair attached.
OFFICER_PAGES pins that county's direction, and its URL besides, because a
county may state its officers on a page other than its district list.

The strict readings exist because a district whose own row yields no readable
name reaches past the next heading and takes ITS name: Rusk prints an INDEX of
nineteen bare "District #N" links above its roster, and Richland's rows end in
an e-mail address. Both filed one person under two districts, both were caught
by the duplicate-name guard below, and neither ships. They are a separate
strategy rather than a change to `_windowed` so the twenty counties already
shipping keep byte-identical behaviour.

A sixth joined on 2026-08-29, and it is the first that is not one shape at all:

    same-line-or-next
                BOTH of the first two, in one page (Iowa) — see
                `_same_line_or_next`
MONROE READS ITS TABLE AS A TABLE (added 2026-08-29)
----------------------------------------------------
Monroe publishes a real HTML table — District | Municipal Ward | Supervisor |
Address | Phone | Email, one row per seat — and none of the five line readings
above is safe on it. Its ward cells run to six lines, which is past
COLUMN_SPAN, and the page carries a MONTH'S EVENT CALENDAR above the table:
seventy-odd bare numerals in the district range, each followed by a time and
an event title. `_column` would be reading a calendar for the numbers it keys
on, and one month's event named after a person would seat that person.

So `_monroe` reads the ROW, and locates its columns BY THEIR HEADER NAMES
rather than by position, so a column reordered upstream cannot shift a roster
and a column renamed fails loudly. Two witnesses per row: the District cell
and the local part of the row's own e-mail address
(district.07@co.monroe.wi.us), which the county maintains per seat — they must
agree, or the row is refused. Home addresses and phone numbers sit in that
table and are NOT carried: the addresses are supervisors' houses (the standing
fleet rule), and this instance's roster file has no phone field for the numbers
to ride — they are personal numbers printed beside those homes, and Taylor's
are dropped by the same builder for the same reason.

A COUNTY THAT DOES NOT FULLY RESOLVE YIELDS NOTHING. Partial output is worse
than none here: a card showing 18 of 21 districts reads as a complete board
with three empty seats. The same rule governs the per-supervisor CONTACT a
county publishes (MEMBER_PAGES), with floors set to catch a page template
reshaping rather than one supervisor's row changing.

OFFICERS PUBLISHED ABOVE THE DISTRICT LIST (added 2026-08-27)
--------------------------------------------------------------
Seven counties name their chair and vice-chairs in a block of their own rather
than beside the member's district row, so `split_role` — which only sees a role
attached to the name it is reading — never reached them. That is not cosmetic:
the county card's board chair is reconciled weekly against this roster, and a
roster with NO marked chair makes the officer builder WITHHOLD the Blue Book's
chair rather than supersede it. Attaching those roles took Juneau's and
Winnebago's cards from a withheld chair to the right one (the book still had
Timothy Cottingham and Thomas J Egan; their counties say Jim Cauley and Frank
Frassetto), and cut the withheld count from three to one.

`attach_officer_roles` joins on a UNIQUE FULL NAME and prints every join. It
never overwrites a role a member's own row already carries, and it walks into
the same before/after ambiguity the rest of this file pins per county — see
its comment for the three cases and for Jefferson, which a forward-only first
draft filed one seat off.

A SIXTH SHAPE, AND THE ONE THAT NEEDS NO DIRECTION AT ALL (2026-08-29)
----------------------------------------------------------------------
    row         a TABLE ROW pairing the two cells (Rock) — see `_rows`

Rock County publishes its board as a Granicus staff-directory TABLE, one
`<tr>` per supervisor holding `<td>Fleming, Patricia</td><td>District 01
Supervisor</td>`. Flattened to lines that reads as a `before` page — and it is
the sharpest example this file has of why the flattening is dangerous. The
`after` reading of the SAME page also resolves 29 of 29, names 29 DIFFERENT
people, every one of them their neighbour's supervisor, and files the site's
own footer — "Website design by Granicus" — as District 29. Both readings pass
every count guard; only the duplicate-name guard would have anything to say,
and it has nothing, because a shift by one duplicates nobody.

So Rock is not read by pinning a direction around the ambiguity. The county
wrote the pairing in a ROW, and `_rows` reads it there, where the ambiguity
does not arise: one district per row, one name per row, or the row is skipped
and the count guard fails loudly. THE ROW READING IS THE FIRST CHOICE FOR ANY
COUNTY WHOSE PAGE IS A TABLE; the line readings remain for the pages that are
lists and prose.

A REFUSED SITE IS NOT A REFUSED PAGE: ROCK AND THE ARCHIVE LADDER (2026-08-29)
------------------------------------------------------------------------------
co.rock.wi.us answers HTTP 403 from AkamaiGHost to EVERY request this project
can make: the board page, the front door, robots.txt and sitemap.xml alike,
under a Chrome user-agent, under a named bot user-agent and under curl's
default. A block that covers robots.txt is not a page refusing a reader and
not a header this client got wrong — it is the edge refusing this client's
network, and there is nothing about the request to fix. (The county's own GIS
is a separate host and publishes no supervisor names anyway: its supervisory
district service is an internal `.lan` URL, and its public service sits on
port 8443, which this project's egress does not reach.)

What the county publishes is nonetheless PUBLIC and ARCHIVED. The Internet
Archive holds the board page, so Rock is read from the newest capture rather
than not at all — the "engine ladder" the fleet already runs for blocked
counties, with the rung that answered recorded on the county's own entry
(`read_from`, which carries the capture's timestamp) instead of being passed
off as a live read.

THIS IS NOT TAYLOR'S CASE AND MUST NOT BECOME IT. Taylor rides
DOCUMENT_ROSTERS because a captcha admits only a human, so its roster cannot
be re-read by anything here and says so, dated, on every run. Rock's page is
re-fetched in full on every run — from the Archive rather than the county, but
fetched, parsed and count-guarded exactly like the other thirty. A capture is
a fetch; a document in this file is not.

Two things keep that honest.

  THE LADDER STARTS LIVE. `fetch_or_archive` asks the county first, every run,
  and only falls to the Archive on a refusal. The day Akamai stops refusing,
  Rock reads live with no code change, and the run log says which rung answered.

  A CAPTURE MUST POST-DATE THE BOARD IT NAMES. Wis. Stat. 59.10(3)(d) elects
  every supervisor in this class of county "for 2-year terms at the election to
  be held on the first Tuesday in April in even-numbered years", to "take office
  on the 3rd Tuesday in April of that year" — so a capture older than the most
  recent 3rd Tuesday in April of an even year shows a board that no longer
  sits. `board_seated_on` computes that date and the fetch REFUSES an older
  capture rather than shipping a stale roster under a current-looking card.
  Rock's board was seated 21 April 2026; the captures of 2026-06-04 and
  2026-08-14 both clear it, agree with each other on all 29 districts and on
  all three officers, and the second is what ships.

The chair the page names is a third witness on top of that: the Wisconsin Blue
Book (April 2025) already had Kevin Leavy as Rock's board chair, independently
of the county's own page, and the officer builder reconciles the two.
WHERE THE ARCHIVE ROUTE SITS AMONG THE EIGHT (2026-08-29)
---------------------------------------------------------
The eight carriers are listed at the top of this file. ARCHIVE_COUNTIES is the
one that needs its reasoning
stated. Fond du Lac's directory is richer than most of the pages that already
ship — name, district, county e-mail and phone for all twenty-five seats, the
Chair and both Vice Chairs titled — and www.fdlco.wi.gov answers this client
HTTP 403 from AkamaiGHost on every path, every user-agent and both schemes.
The county is not withholding anything; a CDN is refusing a datacenter
address. The Internet Archive's crawler has been taking copies of that same
public page for years, so the page is read from there.

THE LINE THIS SITS ON. A captcha is an access control and is never worked
around here (Taylor is the standing example). A client-fingerprint 403 is not
defeated either — nothing in this file forges a fingerprint or retries the
county's own server in disguise. Reading a public archive of a public page is
a third party's copy of a document the county published to the world, and it
is the arrangement Illinois already runs for Kendall and McHenry. The
difference from Taylor is not politeness, it is REPEATABILITY: an archive can
be re-read every week and a browser session in someone's memory cannot.

WHICH IS WHY FRESHNESS IS GATED AND NOT ASSUMED. The failure mode of an
archive is not a wrong answer, it is a stale one that looks current — see the
two measurements recorded above ARCHIVE_COUNTIES, one of which would have
stitched five supervisors from before an April election onto twenty from
after it. Save Page Now is asked for a new copy on every run, the copy's age
is checked before it is parsed, and the pages must have been captured close
together. A county that cannot be read FRESHLY is skipped for that run,
exactly like a county whose page has reshaped.
MANITOWOC PUBLISHES A PAGE PER SUPERVISOR, AND IT IS WORTH FETCHING (2026-08-29)
-------------------------------------------------------------------------------
Every row of Manitowoc's list links a personnel page for that supervisor, and
each of those pages carries three things the list does not:

  * "Supervisory District: N" — the county stating the SAME pairing a second
    time, on a page written by a different part of its own site. Nothing here
    infers Manitowoc's pairing (the number is on the name's own line), so the
    witness is not load-bearing; it is a tripwire, and a DISAGREEMENT is fatal
    while an absence only prints — failing the county over its SECONDARY pages
    would delete twenty-five supervisors the list page still names. The whole
    file exists because a roster can be full, plausible and shifted by one.
  * a county e-mail on the county's own domain — the contact the card exists to
    surface, for a board that publishes nothing else machine-readable.
  * the page itself, which ships as `profileUrl`.

THE E-MAILS ARE OBFUSCATED TWICE AND BOTH LAYERS ARE THE PAGE'S OWN. Cloudflare
rewrites the `mailto:` into a `data-cfemail` hex blob whose first byte is an XOR
key — the markup that silently emptied Brown County's (Illinois) seven addresses
and is decoded all over this fleet. Decoding it here yields
`09x5ry1yy18s1635@x9w1qvnv77vpwqln1.3vo`, which is not a mistake: underneath
sits the site theme's OWN scramble, undone in the browser by the
`replace-html-with-email` handler on every one of those links. It reverses the
36-character alphabet "a…z0…9" — a↔9, i↔1, m↔x, o↔v, punctuation untouched —
and it is an involution, so `unscramble` is its own inverse and
`jameslillibridge@manitowoccountywi.gov` comes back out.

TWO LAYERS OF OBFUSCATION IS STILL A PUBLISHED ADDRESS. Both layers run in
every visitor's browser and neither is an access control: the page is served
whole to any client, and the county gives its supervisors addresses on
`manitowoccountywi.gov` precisely so constituents can write to them. Compare
Taylor above, where a captcha IS an access control and is not defeated. As
everywhere in this fleet, markup-present-but-nothing-decoded is a HARD FAILURE
rather than a quietly empty column.

THE STREET ADDRESS AND TELEPHONE ON THOSE PAGES ARE NOT READ. They are
supervisors' homes and home lines ("2514 S 8th St", a residential number), and
this fleet does not publish where an official lives — the same rule Taylor's
document roster, Warren's parser and Madison's and Peoria's builders follow. No
Wisconsin board roster carries a phone field at all.

NO CHAIR IS MARKED FOR MANITOWOC, AND THAT IS MEASURED RATHER THAN MISSED. Three
county-published surfaces were read on 2026-08-29 and none of them marks a chair
in a form this file can use:

  * the 25 personnel pages all title their subject "County Board Supervisor" —
    the title IS read (`PROFILE_TITLE`), so a chair the county labels on their
    own page would attach itself; today none is;
  * the county's own 2025-26 directory PDF (printed September 2025) names
    "Chairperson of the County Board  Tyler Martell", and the Wisconsin Blue
    Book (April 2025) agrees — but Martell is not among the 25 supervisors the
    county publishes today, and neither is the directory's Second Vice-Chair.
    Both documents predate the April 2026 spring election that reseated the
    board;
  * the board's landing page carries a "Chairman Welcome Letter" signed
    "Matthew Phipps", who IS a sitting supervisor (district 21), above a board
    photograph uploaded in June 2026.

That last one is the county saying something real, and it is still not used: the
role would come from a page TITLE and the name from a SIGNATURE six paragraphs
below it, which is an inference about document structure, not a label beside a
name — and a letter left up through a chair rotation would ship the wrong chair
silently. A role guessed onto the wrong supervisor is worse than no role at all.
The consequence is deliberate and is an improvement: with no marked chair and
the Blue Book's chair ABSENT from a complete roster,
build_wi_county_officer_roster.py withholds Tyler Martell instead of naming a
man who has left the board. THAT LANDS ON THE NEXT WEEKLY RUN, not in the
commit that added this county: the officer rebuild needs the Blue Book PDF
re-parsed and all 44 open county officer pages re-read, and doing either from a
vantage that reaches fewer counties than the runner does would ship a worse
file than the one already committed. update-wi-county-board-roster.yml runs
both steps beside this scrape every Thursday. To supersede the withhold rather
than merely earn it, Manitowoc needs a source that labels its chair beside
their own name and can be re-read every week.

Vacancies are DATA, not misses. Winnebago district 33 ("Vacant Vacant"),
Shawano 5, Oneida 1 and Rusk 3 and 13 are seats the counties themselves say
nobody holds; they ship as vacant, and a vacancy overrides any name the search
window happens to reach. `vacant_districts` only scans FORWARD from the word
"district", which is why the strict and column readings report their own:
Shawano prints "Vacant ." ABOVE its "- District 5", and a column page names no
district beside a seat at all.

Usage:
    python3 wi/scripts/wi_county_board_scraper.py [--out PATH] [--only FIPS]
"""

import datetime
import gzip
import html as html_lib
import io
import json
import os
import random
import re
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

DEFAULT_OUT = os.path.join(os.path.dirname(__file__), ".cache", "wi_county_boards_raw.json")
# A CHROMIUM USER-AGENT WITHOUT CHROMIUM'S CLIENT HINTS IS A CLIENT THAT
# CONTRADICTS ITSELF, and Akamai's bot manager scores exactly that. This dict
# used to carry the first three headers alone, and nine counties were recorded
# below as answering 403 "and holding it against browser headers" — but every
# real Chromium sends `Sec-CH-UA`, `Sec-CH-UA-Mobile` and `Sec-CH-UA-Platform`
# beside that UA, and an `Accept-Encoding` of some kind, so the header set was
# never a browser's. Measured on Sheboygan 2026-08-29 by leave-one-out over a
# full Chrome header set: the UA string is not the variable (the old
# Chrome/124.0 string works unchanged once the hints are present) and neither
# is anything Sec-Fetch-*; adding the three hints plus Accept-Encoding turns a
# reproducible 403 into a reproducible 200. Re-probing the other eight
# recorded counties the same day, seven more answered — see WHAT THE HEADER FIX
# RETIRED above, including why the first re-probe read as four.
#
# `Accept-Encoding: identity` rather than gzip on purpose: urllib does not
# decompress for you, and `fetch` below decodes the body as text. The header's
# PRESENCE is what the scorer wants; its value is free.
#
# THE HEADERS ARE NOT THE WHOLE FINGERPRINT, and the difference is worth
# knowing before anyone ports this fix into another tool: with these exact
# headers Sheboygan's host answers stdlib `urllib` 200 and `requests` 403.
# curl behaves like urllib. The discriminator is below HTTP — urllib3's TLS
# ClientHello differs from the stdlib ssl module's and the manager
# fingerprints it — so copying this dict into a requests-based script
# reproduces nothing. wi/scripts/validate_sources.py probes these two rows
# through their own `scraper_get` for exactly that reason.
# WHAT THIS FILE SENDS, AND THE MEASUREMENT THAT CHOSE IT (2026-09-12)
# -------------------------------------------------------------------
# THE DISTRICTRY TOKEN IS THE DEFAULT. Until this date it was the spoofed
# Chrome string below, for every host, on no measurement — while the fleet rule
# is that a scraper starts with a token and reaches for a browser string only
# where a site refuses the token (CLAUDE.md, "Browser user-agent strings"). So
# every host this file fetches was asked for ITS OWN page, on THIS file's stack
# (stdlib urllib) and header shape, with the token:
#
#     67 of 74   HTTP 200, 6.9 KB to 7.7 MB of county page
#      6 of 74   HTTP 403                      -> TOKEN_REFUSED_HOSTS below
#      1 of 74   HTTP 202, 196 bytes           -> co.taylor.wi.us, whose every
#                                                 path answers that meta-refresh
#                                                 to every client; it rides
#                                                 DOCUMENT_ROSTERS and is not
#                                                 fetched, so it is not pinned
#
# ONE OF THE 67 HAS SINCE MOVED, and saying so is the difference between a
# measurement and a claim: www.lafayettecountywi.org/bos served the token
# 71,648 bytes that morning and answered 403 to BOTH clients two hours later.
# Its record in the docstring above already calls it intermittent. It is not
# pinned, because a pin says "this host wants the Chrome string" and this host
# refuses that too.
#
# THE HOST SWEEP ALONE WAS NOT ENOUGH, and the two hosts it missed are worth
# naming. It walks the URL literals in THIS file, so it never asked
# racinecounty.gov (Racine rides ARCGIS_COUNTIES and its site is read by
# nothing here) or www.co.sauk.wi.us (Sauk's board sits on saukdomino, a
# different host). Both refuse the token — 403 and a reset connection — and
# both serve Chrome/124 a full page, and both are reached by
# build_wi_county_board_directory.py, which asks headers_for. They turned up
# only when that builder's own 72 roots were probed with the new default. A
# HOST-KEYED PIN IS ONLY AS COMPLETE AS THE HOST LIST IT WAS BUILT FROM.
#
# TWO DISAGREEMENTS WITH THE FLEET SWEEP (user-agent-measurements.json), each a
# different lesson. www.wausharacountywi.gov is the STACK: 403 to `requests` +
# the token, 200 to stdlib + the same token, which is why a verdict measured
# with another client does not transfer. saukdomino.co.sauk.wi.us is the PATH:
# the sweep read 404 at the URL it picked and this file's own URL serves
# 113,018 bytes. The sweep also files nine of these hosts
# `robots-disallows-this-path`, again for the path IT picked; all nine of this
# file's own URLs on those hosts are permitted, read through
# scripts/robots_policy.py with the token before each fetch in the count above.
#
# The client hints below say Chromium while the User-Agent says districtry,
# which is two answers to one question. They are kept because they are what was
# measured; dropping them is a separate change and needs its own probe.
UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "identity",
    "sec-ch-ua": '"Chromium";v="124", "Not;A=Brand";v="24"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
}

# The same headers, saying what this client is. The two sets differ in ONE
# line, which is what makes the count above a measurement of the token rather
# than of the header shape.
HONEST_UA = dict(UA, **{
    "User-Agent": "districtry-roster-bot/1.0 (+https://districtry.com/; "
                  "weekly county board roster refresh)",
})

# The hosts still asked as Chrome/124, with what each answered the token on
# 2026-09-12. Per HOST, because the rule belongs to the edge rather than to the
# county's page shape, and PINNED rather than negotiated at runtime so a weekly
# run sends identical bytes every week — a ladder that retried on 403 would
# make the request that actually worked invisible in the log.
#
# BOTH SPELLINGS OF SIX HOSTS ARE LISTED, and that is measured rather than
# tidy. This file asks for `www.co.monroe.wi.us`; build_wi_county_board_
# directory.py probes the same county as `co.monroe.wi.us` and asks this
# function which client to use. A set keyed on the exact hostname answers
# "token" for the bare form, which would make that probe a weaker client than
# the crawl on the four counties it most needs to reach. Stripping `www.` in
# the lookup would assume the two names share an edge; asking them instead
# (2026-09-12, same minute) found they do — and found `fdlco.wi.gov` does not
# behave like its sibling, which a fold would have hidden.
TOKEN_REFUSED_HOSTS = {
    "co.monroe.wi.us": "HTTP 403",
    "co.rock.wi.us": "HTTP 403",
    "fdlco.wi.gov": "TLS: UNEXPECTED_EOF_WHILE_READING — no client reaches it",
    "lacrossecounty.org": "HTTP 403",
    "marathoncounty.gov": "HTTP 403",
    "racinecounty.gov": "HTTP 403; Chrome/124 gets 125,639 bytes",
    "sheboygancounty.com": "HTTP 403",
    "www.co.monroe.wi.us": "HTTP 403",
    "www.co.rock.wi.us": "HTTP 403",
    "www.fdlco.wi.gov": "HTTP 403",
    "www.co.sauk.wi.us": "connection reset, twice; Chrome/124 gets 48,614 bytes",
    "www.marathoncounty.gov": "HTTP 403",
    "www.racinecounty.gov": "HTTP 403; Chrome/124 gets 125,640 bytes",
    "www.sheboygancounty.com": "HTTP 403",
}

# BROWSER AND BROWSER_HEADER_COUNTIES WERE RETIRED HERE, BECAUSE THEY HAD NOT
# REACHED THE WIRE SINCE 206cb9c (2026-08-29). That commit gave fetch_bytes a
# line of its own — `headers = HONEST_UA if host in HONEST_UA_HOSTS else UA` —
# which overwrote whatever header set its caller had chosen. So the Monroe pin
# the docstring above describes at length was sent on no run, and Monroe has
# been read with UA all along: 16 seats on 2026-09-10, like every other week.
# The clobber did real damage elsewhere. fetch_archived hands `fetch` the
# ARCHIVE_UA this file measured web.archive.org answering 200 to and the Chrome
# string it measured getting 503, and the clobber substituted the second — so
# the archive rung, which exists for the counties whose own sites refuse this
# client, has been asking with the one client the archive was known to refuse.
# fetch_bytes now honours the set it is handed.


def headers_for(url):
    """The header set this host is asked with — pinned, never negotiated.

    Takes a URL or a bare host, because wi/scripts/validate_robots.py asks by
    host. That gate reads robots.txt with the client that does the crawling,
    which means asking here rather than re-deriving the answer beside it.
    """
    host = urllib.parse.urlsplit(url).hostname or url
    return UA if host in TOKEN_REFUSED_HOSTS else HONEST_UA

# (county FIPS, name as LTSB spells it, seats, reading direction, page)
COUNTIES = [
    ("55007", "Bayfield", 13, "same-line",
     "https://bayfieldcounty.wi.gov/295/Board-of-Supervisors"),
    ("55009", "Brown", 26, "before",
     "https://www.browncountywi.gov/government/county-board-of-supervisors/"),
    ("55013", "Burnett", 21, "same-line",
     "https://burnettcountywi.gov/264/Supervisors"),
    ("55035", "Eau Claire", 29, "same-line",
     "https://eauclairecounty.gov/board_of_supervisors/district_representatives.php"),
    ("55043", "Grant", 17, "same-line",
     "https://co.grant.wi.gov/"),
    ("55045", "Green", 31, "before",
     "https://greencountywi.org/164/County-Board-of-Supervisors"),
    ("55055", "Jefferson", 30, "same-line",
     "https://jeffersoncountywi.gov/county_government/county_board/county_board_information/index.php"),
    ("55077", "Marquette", 17, "before",
     "https://www.marquettecountywi.gov/government/county-board-supervisors/"),
    ("55097", "Portage", 25, "before",
     "https://www.co.portage.wi.gov/171/County-Board"),
    ("55123", "Vernon", 19, "same-line",
     "https://www.vernoncountywi.gov/government/county_board_of_supervisors/index.php"),
    ("55125", "Vilas", 21, "after",
     "http://www.vilascountywi.gov/departments/administration___officials/county_board_members/index.php"),
    ("55127", "Walworth", 11, "before",
     "https://co.walworth.wi.us/534/Board-of-Supervisors"),
    ("55129", "Washburn", 21, "after",
     "https://co.washburn.wi.us/county-board-supervisors/"),
    ("55131", "Washington", 21, "same-line",
     "https://www.washcowisco.gov/departments/county_board"),
    ("55133", "Waukesha", 25, "same-line",
     "https://www.waukeshacounty.gov/waukesha-county-board/county-board-supervisors/"),
    ("55137", "Waushara", 11, "after",
     "https://www.wausharacountywi.gov/13370/county-board-of-supervisors"),
    ("55139", "Winnebago", 36, "after",
     "https://www.winnebagocountywi.gov/703"),
    ("55141", "Wood", 19, "after",
     "https://woodcountywi.gov/CountyBoard/"),
    # --- the 2026-08-27 re-sweep: ten counties that were publishing all along ---
    # Dane's list is on the BOARD's host, not the county's — the county site was
    # checked and board.danecounty.gov was not.
    ("55025", "Dane", 37, "after",
     "https://board.danecounty.gov/Supervisors"),
    ("55057", "Juneau", 21, "same-line",
     "https://www.co.juneau.wi.gov/government/county_board_supervisors/index.php"),
    ("55061", "Kewaunee", 20, "before",
     "https://www.kewauneeco.org/government/boards_and_committees/"),
    ("55075", "Marinette", 30, "same-line",
     "https://www.marinettecountywi.gov/county_board/"),
    ("55085", "Oneida", 21, "column-after",
     "https://www.oneidacountywi.gov/government/cb/"),
    ("55099", "Price", 13, "column-after",
     "https://co.price.wi.us/319/County-Board"),
    ("55115", "Shawano", 27, "before-strict",
     "https://www.co.shawano.wi.us/county_board/"),
    # --- the 2026-08-29 header fix: a county recorded unreadable for a year ---
    ("55117", "Sheboygan", 25, "after",
     "https://www.sheboygancounty.com/departments/county-board/"
     "county-board-supervisors"),
    ("55121", "Trempealeau", 17, "column-before",
     "https://co.trempealeau.wi.us/government/agendas_minutes/standing_committees/"
     "trempealeau_county_board_of_supervisors.php"),
    # --- 2026-08-29: the county whose SITE refuses this client and whose PAGE
    # does not — read from the Internet Archive, see the docstring's ladder ---
    ("55105", "Rock", 29, "row",
     "https://www.co.rock.wi.us/government/county-board-of-supervisors"),
    # ROBOTS.TXT, MEASURED 2026-08-29 AND RECORDED RATHER THAN DISCOVERED
    # TWICE. Two of the fifty counties publish a robots.txt with a site-wide
    # Disallow aimed at AI crawlers by name — IOWA (anthropic-ai, ClaudeBot,
    # Claude-Web, GPTBot, CCBot) and WAUSHARA (ClaudeBot, GPTBot, CCBot), which
    # has been shipping since before this route existed. In BOTH files the
    # `User-agent: *` group permits the board path (it disallows only
    # /calendar, /meetings, /media, /portal, /311 and /newsletters) with
    # crawl-delay 5, and this scraper is a weekly single-page civic fetch that
    # claims to be none of the named agents. The operator's decision (2026-08-29)
    # is to read the page the `*` group allows and to write the measurement down
    # here, so the next person meets it as a recorded fact rather than as a
    # surprise. A county that moves the board path under a Disallow, or that
    # asks directly, is a different question and this note is where to start.
    # --- 2026-08-29: the county whose own home page links no path to it ---
    ("55049", "Iowa", 21, "same-line-or-next",
     "https://www.iowacountywi.gov/departments/countyboard/county-board-members"),
    # --- 2026-08-29: the county this file spent four days calling map-only ---
    # The BOARD page, not the /2206/Supervisory-District-Maps page the
    # directory holds. `column-after` is load-bearing: read the other way the
    # page yields a full 25-seat roster built out of the ADDRESS column, with
    # the vacancy silently gone. See the Ozaukee section of the docstring.
    ("55089", "Ozaukee", 26, "column-after",
     "https://ozaukeecounty.gov/701/County-Board"),
    # --- 2026-08-29: Crawford, an eleventh county whose "publishes nothing"
    # record was ours. Its page is `after` in shape (District heading, the word
    # "Supervisor", then the name) and pinned STRICT: a district whose block
    # loses its name must fail the count guard, never reach nine lines down
    # into its neighbour's. Both readings resolve 17/17 and agree.
    ("55023", "Crawford", 17, "after-strict",
     "https://www.crawfordcountywi.gov/boardsupervisors"),
    # --- 2026-08-29: a county recorded as publishing nothing, publishing the
    # richest list in the fleet. See INDEXROLL below.
    ("55047", "Green Lake", 19, "indexroll",
     "https://www.greenlakecountywi.gov/officials_type/county-board-supervisors/"),
    # --- 2026-08-29: the first county read by its page's own FIELD LABELS ---
    # co.sauk.wi.us/countyboard/sauk-county-board-members links this list as
    # "Committee Database: 2026-2028 Sauk County Board Supervisors" under the
    # heading "Term of Office: April 21, 2026 - April 18, 2028", so it is the
    # county's own current-term roster and not a stray application.
    ("55111", "Sauk", 31, "fielded",
     "https://saukdomino.co.sauk.wi.us/Internet/Applications/main.nsf/"
     "publicDistrictList.xsp"),
    # --- 2026-08-29: the county whose 403 was the request, not the county ---
    # Read as a TABLE (see `_monroe`), and as Chrome/124: Monroe is one of the
    # six in TOKEN_REFUSED_HOSTS, 403 to the token on 2026-09-12. It was
    # pinned to a Chrome-navigation header set that fetch_bytes discarded and
    # never sent, so what its weekly runs have always used is the plain set.
    # robots.txt allows this path to every agent; only /scripts,
    # /admin and *.asmx are disallowed.
    ("55081", "Monroe", 16, "table",
     "https://www.co.monroe.wi.us/government/county-board-of-supervisors/"
     "districts-supervisors"),
    # --- 2026-08-29: the sixth page shape, and the first county that links a
    # page per supervisor (see the docstring and `attach_profiles`) ---
    ("55071", "Manitowoc", 25, "numbered-line",
     "https://manitowoccountywi.gov/departments/county-board-of-supervisors/"
     "supervisor-list/"),
    # --- 2026-08-29: the browser UA was the block, see the docstring ---
    # Reads `after`: "District 1" / "Cathy Thompson" / the district's map link,
    # phone, county e-mail and committee. Its host was the first pinned to an
    # honest client string; since 2026-09-12 that is what every county gets.
    ("55087", "Outagamie", 36, "after",
     "https://www.outagamie.gov/Outagamie-County-Board/County-Board-of-Supervisors"),
    # --- 2026-08-31: the 51st county, and the fourth whose "no district-keyed
    # list" record was ours. Calumet was in the 22-county gap block on the
    # strength of a sweep that never opened the page: calumetcounty.org answers
    # 200 with 127 KB to an ordinary browser header set, and names all 21
    # supervisors beside their districts. `cells` is load-bearing and so is the
    # role gate above it — see the `_calumet` comment for both.
    ("55015", "Calumet", 21, "cells",
     "https://calumetcounty.org/243/County-Board-of-Supervisors"),
    # --- 2026-08-31: the 52nd, found the same way as the 51st and one bucket
    # over. Buffalo's record said it "publishes no district-keyed list on the
    # pages their own sites point to"; the page linked from its own Boards &
    # Committees menu names all 14 with a county e-mail for 12. See the
    # `_heading_block` comment for the shape and for the obfuscated addresses.
    ("55011", "Buffalo", 14, "heading-block",
     "https://www.buffalocountywi.gov/government/boards-committees/county-board/"),
    # --- 2026-08-31: the 53rd, and the third out of the same bucket in one day.
    # Jackson's HTML names no supervisor anywhere; its own listing page links a
    # district-keyed roster PDF. See the `scrape_pdf_roster_county` comment for
    # the four traps and for the ward witness that checks its numbering against
    # LTSB's filing.

    # --- 2026-08-31: the 54th. Its BOARD page names nobody at all; the Clerk's
    # Directory of Public Officials, linked from the county's own home page,
    # names all 27 district-keyed. See `scrape_directory_county` for the
    # courthouse-number rule and the two witnesses.
    ("55135", "Waupaca", 27, "directory",
     "https://public4.co.waupaca.wi.us/CountyDirectory"),
    # --- 2026-08-31: the 55th. A CivicPlus staff-directory widget per district,
    # stating the district three ways and gated on all three agreeing. Its page
    # is TWO COLUMNS, so document order is 1,3,5..21,2,4..20 — see the
    # `scrape_staff_directory_county` comment.
    ("55029", "Door", 21, "staff-directory",
     "https://co.door.wi.gov/234/County-Board-of-Supervisors"),
    # --- 2026-08-31: the 56th, and the county this file called map-only for a
    # year. The record described /307/...District-Maps accurately and that is
    # not the roster page; /453/County-Board names all 31. See
    # `scrape_member_cards_county` — its page says "Member", never "Supervisor".
    ("55083", "Oconto", 31, "member-cards",
     "https://www.ocontocountywi.gov/453/County-Board"),
    # --- the 2026-08-29 header fix: a county recorded unreadable for a year ---,
]

# Counties whose own host refuses this client on every path and every header,
# whose page the Internet Archive nonetheless holds. The ladder still asks the
# county FIRST on every run (`fetch_or_archive`); this only says where to look
# when it refuses, and what the refusal measured as.
ARCHIVE_READ = {
    "55105": "co.rock.wi.us answers 403 from AkamaiGHost on every path, "
             "including robots.txt, under every user-agent tried",
}

# The officer block's reading direction, pinned per county, for the counties
# whose officers sit in a run of consecutive name/role pairs. Rock prints
# "Kevin Leavy / Chair / Barbara Tillman / Vice Chair / Ron Woodman / Second
# Vice Chair": every role line has a name on BOTH sides, which is the case
# `attach_officer_roles` deliberately refuses to guess at. The county's own
# table settles it — its Staff column precedes its Title column — so the side
# is PINNED here rather than detected, exactly as the district readings are.
OFFICER_NAME_SIDE = {"55105": "before"}

# --- text shaping -------------------------------------------------------------
# nav is NOT boilerplate everywhere: Grant County publishes its entire board in
# the site navigation, as "District 1 (Gary Ranum)", so it is kept.
_DROP = re.compile(r"(?is)<(script|style)[^>]*>.*?</\1>")
_BREAK = re.compile(r"(?is)<br\s*/?>|</t[dh]>|</tr>|</p>|</li>|</div>|</h\d>|</a>|</span>|</strong>|</b>")
_TAG = re.compile(r"(?s)<[^>]+>")
_FRAGMENT = re.compile(r"[a-z]{1,2}")


def to_lines(page_html):
    h = _BREAK.sub("\n", _DROP.sub(" ", page_html))
    raw = [" ".join(html_lib.unescape(x).split()) for x in _TAG.sub(" ", h).split("\n")]
    out = []
    for x in raw:
        # Markup can strand a word's tail on its own line ("Peg Sheaffe" then
        # "r"); rejoin a short lowercase fragment onto the line above.
        if out and _FRAGMENT.fullmatch(x) and out[-1] and out[-1][-1].isalpha():
            out[-1] = out[-1] + x
        else:
            out.append(x)
    return [x for x in out if x]


# --- name / role / vacancy ----------------------------------------------------
DIST = re.compile(r"(?i)(?:^|[^a-z0-9])district\s*#?\s*(\d{1,2})(?:st|nd|rd|th)?\b")
BAD = re.compile(r"(?i)\b(district|ward|phone|email|map|town|city|village|county|term|"
                 r"expires|chair|vice|contact|supervisor|address|click|more|view|home|"
                 r"menu|search|board|committee|login|election|results|show|again)\b")
SUFFIX = re.compile(r"^(?:I{1,3}|IV|Jr\.?|Sr\.?)$", re.I)
LEAD = re.compile(r"^(?:supervisory|supervisor|county|board|member)\b[\s\-–—:]*", re.I)
# Roles arrive attached to the name in every shape a county can think of.
_ROLE = r"(?:County\s+)?(?:(?:1st|2nd|First|Second)\s+)?(?:Vice[\s\-]?)?Chair(?:man|person|woman)?"
# THE SAME ROLE, PLUS THE WORD `Board`, AND ONLY WHERE IT IS WRITTEN ONTO A
# PERSON'S OWN NAME. Outagamie spells the office out in full on the member's
# row — "Dan Gabrielson, County Board Chairperson" — and without `Board`
# ROLE_TAIL strips only "Chairperson", leaving "Dan Gabrielson, County Board",
# which `is_name` then rejects on its own BAD words (`county`, `board`). So the
# CHAIR of a 36-seat board was the one seat that would not resolve, and the
# all-seats-or-nothing rule correctly refused the whole county for it.
#
# IT IS DELIBERATELY NOT GIVEN TO `OFFICER_LINE`, which matches a role standing
# ALONE on its own line, and that boundary was measured rather than guessed.
# Widening both at once made Dunn mark TWO chairs and the officer builder stop
# the build, which is the guard working: Dunn's district 24 row reads "Chair -
# Randy L. Prochnow", and four hundred lines below the roster a WELCOME LETTER
# to new supervisors is signed "Kelly McCullough / County Board Chairman". A
# bare role line in running prose is a signature, not a roster row, and a
# signature block can outlive its signer — so a role only counts here when the
# county wrote it beside the name it belongs to, or in an officers block whose
# shape `OFFICER_LINE` already recognised.
_ROLE_ATTACHED = r"(?:County\s+)?(?:Board\s+)?(?:(?:1st|2nd|First|Second)\s+)?(?:Vice[\s\-]?)?Chair(?:man|person|woman)?"
ROLE_PAREN = re.compile(r"\s*\((%s)\)\s*" % _ROLE_ATTACHED, re.I)
ROLE_LEAD = re.compile(r"^(%s)\b[\s\-–—:,]*" % _ROLE_ATTACHED, re.I)
ROLE_TAIL = re.compile(r"[\s,\-–—]+(%s)\s*$" % _ROLE_ATTACHED, re.I)
VACANT = re.compile(r"(?i)\bvacan(?:t|cy)\b")
SPLIT_LETTER = re.compile(r"\b([A-Z])\s+([a-z]{2,})")


# str.title() turns "1st Vice Chair" into "1St Vice Chair" — it upper-cases the
# letter after every digit. Ordinals keep their own casing. BOTH role paths
# case through here — `split_role` (a role attached to the name it is
# reading) and `attach_officer_roles` (a county's own officers block). It
# lives up here so the first of those can reach it: `split_role` used a bare
# .title() and shipped Polk's "1St"/"2Nd" vice chairs to the card.
def role_case(text):
    return " ".join(w.lower() if _ORDINAL.match(w) else w.title()
                    for w in text.split())


def repair(name):
    """Rejoin a capital split off its own word by markup ("T homas" -> "Thomas")."""
    return SPLIT_LETTER.sub(r"\1\2", name)


def split_role(text):
    """Return (text_without_role, role_or_None)."""
    role = None
    m = ROLE_PAREN.search(text)
    if m:
        role, text = m.group(1), ROLE_PAREN.sub(" ", text)
    m = ROLE_LEAD.match(text)
    if m:
        role, text = role or m.group(1), ROLE_LEAD.sub("", text)
    m = ROLE_TAIL.search(text)
    if m:
        role, text = role or m.group(1), ROLE_TAIL.sub("", text)
    return " ".join(text.split()), (role_case(" ".join(role.split())) if role else None)


def is_name(text):
    text = split_role(repair(text))[0]
    if not text or not (4 <= len(text) <= 44):
        return False
    if re.search(r"\d", text) or BAD.search(text):
        return False
    toks = [t for t in text.replace(".", "").replace(",", " ").replace("-", " ")
            .replace("'", "").split() if t]
    if not (2 <= len(toks) <= 5):
        return False
    return all(re.match(r"^[A-Za-z][A-Za-z'’\-]*$", t) for t in toks)


# A COMMA-SEPARATED NAME HAS MORE THAN TWO SHAPES, and reading it as two is
# how a suffix ends up where a first name belongs. The four shapes:
#
#     "Coenen, Devon"           Last, First          -> "Devon Coenen"
#     "Schaefer, II"            Last, Suffix         -> "Joseph H. Schaefer II"
#     "Dantinne, Jr., Norbert"  Last, Suffix, First  -> "Norbert Dantinne Jr."
#     "Dantinne, Norbert, Jr."  Last, First, Suffix  -> "Norbert Dantinne Jr"
#
# The third is Brown County's own spelling of its district 13 supervisor, and
# it shipped as "Jr., Norbert Dantinne": a split on the FIRST comma only ever
# sees two fields, so "Jr." was read as the whole of the last name and flipped
# to the front. The county's own profile slug for that member
# (/government/county_board/norbert-dantinne-jr/) is the independent witness
# that Norbert is the first name and Jr. the suffix, which is what makes this
# a PINNED SHAPE rather than a special case for one person.
#
# So every field is split out, the SUFFIXES are lifted aside wherever they
# sit, and only a genuine two-field Last, First is flipped — which leaves the
# two shapes that already shipped byte-identical. The last two rows above are
# therefore the same read, differing only in the trailing period, which the
# strip on the line below has always taken off the END of a name whatever it
# is; Brown writes the third, where the period sits mid-string and survives.
#
# A shape with more than two non-suffix fields is NOT pinned and is not
# guessed at: it joins in the order the county wrote it, so an unread shape
# reads oddly rather than naming somebody wrongly.
# A TRAILING "Jr." OR "M." IS AN ABBREVIATION, NOT STRAY PUNCTUATION, and the
# strip below cannot tell them apart. Two names met it in two days:
# `"George Rohmeyer, Jr."` shipped as "George Rohmeyer Jr" (Chippewa district
# 17, 2026-09-02), and Menominee's `"Wilber,  Dawn M."` came out as "Dawn M
# Wilber" — the middle initial's period eaten before the surname-first flip
# moved it into the middle of the name. Both are the same bug seen from two
# sides, which is why the restore covers a generational SUFFIX and a single
# INITIAL rather than only the case that turned up first. The dot goes back
# only when the ORIGINAL text ended in one of those carrying it, which is the
# only case where removing it changed a name rather than tidying a fragment.
ABBREV_DOT = re.compile(r"(?i)(?:\b(?:I{1,3}|IV|Jr|Sr)|(?<![A-Za-z])[A-Z])\.\s*$")


def clean(text):
    text, role = split_role(repair(text))
    had_abbrev_dot = bool(ABBREV_DOT.search(text))
    text = LEAD.sub("", text).strip(" .,-–—")
    if "," in text:
        fields = [x.strip() for x in text.split(",") if x.strip()]
        suffix = [x for x in fields if SUFFIX.match(x)]
        rest = [x for x in fields if not SUFFIX.match(x)]
        if len(rest) == 2:
            rest = [rest[1], rest[0]]
        text = " ".join(rest + suffix)
    text = " ".join(text.split())
    # The flip above can move the abbreviation into the MIDDLE of the name
    # ("Wilber, Dawn M." -> "Dawn M Wilber"), so the dot is restored on the
    # token it belongs to rather than on the end of the string.
    if had_abbrev_dot:
        parts = text.split()
        for i, tok in enumerate(parts):
            if SUFFIX.match(tok) or re.fullmatch(r"[A-Z]", tok):
                parts[i] = tok if tok.endswith(".") else tok + "."
        text = " ".join(parts)
    return text, role


# --- the three readings -------------------------------------------------------
WINDOW_AFTER = [1, 2, 3, 4, 5, 6, 7]
WINDOW_BEFORE = [-1, -2, -3, -4, -5, -6, -7]


def _same_line(lines):
    out = {}
    for line in lines:
        m = DIST.search(line)
        if not m:
            continue
        rest = re.sub(r"^[\s\-–—:•]+", "", DIST.sub(" ", line, count=1)).strip()
        paren = re.fullmatch(r"\((.+)\)", rest)   # Grant: "District 17 (Brian Lucey)"
        if paren:
            rest = paren.group(1).strip()
        if is_name(rest):
            out.setdefault(int(m.group(1)), clean(rest))
    return out


def _windowed(lines, offsets):
    out = {}
    for i, line in enumerate(lines):
        m = DIST.search(line)
        if not m:
            continue
        d = int(m.group(1))
        if d in out:
            continue
        for off in offsets:
            j = i + off
            if 0 <= j < len(lines) and is_name(lines[j]):
                out[d] = clean(lines[j])
                break
    return out


# --- the fourth shape: a district COLUMN ---------------------------------------
# The three readings above all need the WORD "district" next to the number,
# because that is how a page written as prose or as a list says it. A page
# written as a TABLE says it once, in the column header, and then prints bare
# numerals in the cells:
#
#     District | Name            | Phone        (Oneida: number then name)
#     1        | Vacant          |
#     2        | Sandy Hamburg   | 715-499-3129
#
#     Members          | Phone        | District   (Trempealeau: name then number)
#     Andy Todd, Chair | 608-406-0616 | 5
#
# `DIST` cannot see either, so all three column counties were recorded as
# publishing "no district column" — when having one is precisely why they were
# unreadable. Found 2026-08-27 re-sweeping the 50 no-roster counties, after
# Trempealeau turned out to publish the roster this project was drafting an
# e-mail to ask it for.
BARE_NUM = re.compile(r"^#?\s*(\d{1,2})\s*$")
COLUMN_SPAN = 6
# Richland publishes "Melvin (Bob) Frank" — a parenthesised nickname, which
# `is_name`'s per-token test rejects. The nickname is stripped for the TEST
# only: what ships is the county's own spelling, parentheses and all.
NICKNAME = re.compile(r"\s*\([^)]{1,24}\)\s*")


def _reads_as_name(cell):
    return is_name(cell) or is_name(NICKNAME.sub(" ", cell).strip())


def _column(lines, seats, forward):
    """Pair a bare-numeral district cell with the nearest name cell.

    The scan STOPS at the next bare numeral in range: without that, a district
    whose own row carries no readable name would reach into its neighbour's row
    and every seat below it would shift by one — the same failure the pinned
    reading directions exist to prevent, one column over.
    """
    out, vacant = {}, set()
    step = 1 if forward else -1
    for i, line in enumerate(lines):
        m = BARE_NUM.match(line.strip())
        if not m:
            continue
        d = int(m.group(1))
        if not (1 <= d <= seats) or d in out or d in vacant:
            continue
        for off in range(1, COLUMN_SPAN + 1):
            j = i + off * step
            if not (0 <= j < len(lines)):
                break
            cell = lines[j].strip()
            if BARE_NUM.match(cell):
                break                       # the next row: this one has no name
            if VACANT.search(cell):
                vacant.add(d)
                break
            if _reads_as_name(cell):
                out[d] = clean(cell)
                break
    return out, vacant


def _windowed_strict(lines, offsets):
    """`_windowed`, but the scan STOPS at the next district line.

    Rusk prints an INDEX of nineteen bare "District #N" links above its roster,
    and Richland's rows end in an e-mail rather than a name. In both, a district
    whose own row yields no readable name reaches past the next district heading
    and takes ITS name — Rusk filed Alec Hampton under both 19 and 1, Richland
    filed Kerry Severson under 15 and 16. The duplicate-name guard caught both,
    which is what it is for; this reading removes the cause. It is a separate
    pinned strategy rather than a change to `_windowed` so the twenty counties
    already shipping keep byte-identical behaviour.
    """
    out, vacant = {}, set()
    for i, line in enumerate(lines):
        m = DIST.search(line)
        if not m:
            continue
        d = int(m.group(1))
        if d in out or d in vacant:
            continue
        for off in offsets:
            j = i + off
            if not (0 <= j < len(lines)):
                break
            if DIST.search(lines[j]):
                break               # the next district's row: stop, never borrow
            # A vacancy sits on the side the page reads from: Shawano prints
            # "Vacant ." ABOVE its "- District 5", where the forward-only
            # `vacant_districts` can never see it.
            if VACANT.search(lines[j]):
                vacant.add(d)
                break
            if _reads_as_name(lines[j]):
                out[d] = clean(lines[j])
                break
    return out, vacant


# --- the fifth shape: the office BETWEEN the name and the district -------------
# Lafayette writes each seat as one line with the person FIRST and the district
# LAST, the office sitting between them:
#
#     Larry Ludlum- Supervisor District #1
#     Jack Sauer- County Board Chairman District #3
#
# `_same_line` strips the district and tests what is left, and what is left ends
# in "Supervisor" — a word `BAD` rejects, and rightly: it is the word that makes
# a heading a heading everywhere else. So the county read as publishing nothing
# while publishing all sixteen seats in the plainest form on this list. The
# reading takes the text BEFORE the district and strips the office off its tail,
# which is also where the ROLE is: the chairman's own row says so, where every
# other county on this list needs `attach_officer_roles` to reach a block
# further up the page.
_OFFICE_ROLE = r"(?:(?:County\s+)?Board\s+)?%s" % _ROLE
LEAD_OFFICE = re.compile(r"^(?P<name>.+?)[\s,\-\u2013\u2014]+(?P<office>(?:Supervisor|%s))\s*$"
                         % _OFFICE_ROLE, re.I)


def office_role(office):
    """The office as a ROLE, or None when it is the plain seat.

    Every member of a county board is a supervisor, so "Supervisor" is the
    office and not a role — shipping it as one would put "Supervisor
    (Supervisor)" on the card. Anything else is trimmed to the words that
    distinguish it ("County Board Chairman" -> "Chairman"), which is the
    vocabulary the other counties' rows already use and the vocabulary
    build_wi_county_officer_roster.py's `marks_chair` reads.
    """
    office = " ".join(office.split())
    if office.lower() == "supervisor":
        return None
    return role_case(re.sub(r"(?i)^(?:county\s+)?(?:board\s+)?", "", office))


def _same_line_lead(lines):
    out, vacant = {}, set()
    for line in lines:
        m = DIST.search(line)
        if not m:
            continue
        d = int(m.group(1))
        if d in out or d in vacant:
            continue
        # DIST consumes the separator before "district", so the head is the
        # whole of the line the county wrote before naming the district. A page
        # of this shape states a vacancy on that same line, which is the
        # `vacant_districts` lesson Marinette taught, one reading over.
        head = line[:m.start()].strip(" \t\u2013\u2014-:\u2022,")
        if VACANT.search(head):
            vacant.add(d)
            continue
        om = LEAD_OFFICE.match(head)
        if not om or not _reads_as_name(om.group("name")):
            continue
        who, role = clean(om.group("name"))
        out[d] = (who, role or office_role(om.group("office")))
    return out, vacant


# Lafayette's chair and both vice-chairs are named again in an administration
# block above the seat list, as "Name, Role" — the reverse of the "Role - Name"
# shape `attach_officer_roles` reads, and unreachable by it. This is a separate
# pass rather than a widening of that function so the counties already shipping
# keep byte-identical behaviour, and it obeys the same two rules: the join is on
# a UNIQUE FULL NAME, and every join prints.
#
# The role must match to the END of its own line, which is what keeps the
# county's own rules text out of it: "Memorial Hospital Compensation Oversight
# Committee (Cty Bd Chair, First Vice Chair and 3 Cty Bd members...)" carries
# both the comma and the words and is not a roster row. It is also what drops
# "Carla M Jacobson, County Clerk" — the clerk is not a supervisor, and the
# county's own clerk record is a different file.
NAMED_OFFICER = re.compile(r"^(?P<name>[^,]{4,44}),\s*(?P<role>%s)\s*$"
                           % _OFFICE_ROLE, re.I)


def attach_named_officer_roles(lines, districts, county):
    by_name = {}
    for d, row in districts.items():
        if row.get("name"):
            by_name.setdefault(row["name"], []).append(d)
    for line in lines:
        m = NAMED_OFFICER.match(line)
        if not m or not is_name(m.group("name")):
            continue
        role = office_role(m.group("role"))
        if not role:
            continue
        who = clean(m.group("name"))[0]
        hits = by_name.get(who)
        if not hits:
            continue                    # named above the list but not on it
        if len(hits) > 1:
            print("  note %-12s %r holds %d districts \u2014 role %r not attached"
                  % (county, who, len(hits), role), file=sys.stderr)
            continue
        if districts[hits[0]].get("role"):
            continue                    # the seat's own row already said so
        districts[hits[0]]["role"] = role
        print("  role %-12s district %s: %s -> %s"
              % (county, hits[0], who, role), file=sys.stderr)
    return districts


# --- the sixth shape: a TABLE ROW ---------------------------------------------
# The five readings above all pair a district with a name by POSITION in a
# flattened line list, which is why four of them have to pin a direction. A
# page that writes the pairing into a table row does not need one — Rock's
# markup is literally
#
#     <tr><td>Fleming, Patricia</td><td>District 01 Supervisor</td>
#         <td>County Board</td><td>(608) 719-7943</td><td>Email</td></tr>
#
# so the district and its supervisor are in the same row, in whichever order
# the county likes. Read there, a shift by one cannot happen; read as lines,
# Rock's `after` reading resolves all 29 seats, names everybody's neighbour
# and files the page footer as District 29 (see the docstring).
#
# ONE DISTRICT AND ONE NAME PER ROW, OR THE ROW IS SKIPPED. A row that carries
# two of either is ambiguous, and a skipped row fails the caller's count guard
# loudly — which is the whole point of not guessing.
_ROW = re.compile(r"(?is)<tr[^>]*>(.*?)</tr>")


def _rows(page_html, seats):
    out, vacant = {}, set()
    for row_html in _ROW.findall(page_html):
        cells = to_lines(row_html)
        dists = {int(m.group(1)) for m in (DIST.search(c) for c in cells) if m}
        if len(dists) != 1:
            continue
        d = dists.pop()
        if not (1 <= d <= seats) or d in out or d in vacant:
            continue
        if any(VACANT.search(c) for c in cells):
            vacant.add(d)
            continue
        named = [c for c in cells if not DIST.search(c) and _reads_as_name(c)]
        if len(named) == 1:
            out[d] = clean(named[0])
    return out, vacant


# --- the sixth shape: same line OR the next one, in one page ------------------
# Iowa County writes both. SIXTEEN of its districts print "District 1 - Chuck
# Weigel"; the other FIVE (3, 4, 5, 12 and 18) print "District 3 -" and put the
# name on the line below, because the county's editor bolded some names and not
# others and the markup broke where it did. `same-line` resolves those 16 and
# stops.
#
# `after` IS WORSE THAN USELESS HERE RATHER THAN MERELY SHORT, and the
# correction matters more than the original claim did. This comment first said
# `after` resolves 0 of 21 "because every district's own block is address,
# phone and e-mail before the next name appears". Re-measured against the live
# page 2026-08-29: it resolves NINE, and FOUR OF THE NINE ARE THE WRONG PERSON
# — a bare district line reaches forward past its own contact block into the
# NEXT supervisor's name, so D2 files Jody Putz Miller (district 3's member),
# D11 files Keith Hurlbert (district 12's), D17 files Molly Conkey (district
# 18's), and D21 files "General Information", a page heading that passes
# `is_name`. A reading that finds nothing is safe; a reading that names four
# wrong people and still passes a count gate is the exact failure the
# one-line fall-through below exists to prevent. THE ORIGINAL FIGURES DID NOT
# REPRODUCE (14/7 measured as 16/5, 0-of-21 as 9-with-4-wrong) — a recorded
# measurement is a claim and has to survive re-running.
#
# THE FALL-THROUGH IS ONE LINE AND ONLY FROM AN OTHERWISE EMPTY DISTRICT LINE.
# That is what keeps it as safe as the pinned readings it sits beside: a
# district line carrying ANY other text is taken at face value and never looked
# past, so "District 1 Map" — the per-district map link that follows every
# block — cannot reach forward into "District 2 - Ingmar Nelson" and file the
# wrong person. A district whose own line is bare and whose next line is not a
# name simply does not resolve, and the all-seats-or-nothing guard fails the
# county loudly.
def _same_line_or_next(lines):
    out, vacant = {}, set()
    for i, line in enumerate(lines):
        m = DIST.search(line)
        if not m:
            continue
        d = int(m.group(1))
        if d in out or d in vacant:
            continue                    # the heading wins; a later mention cannot move it
        rest = re.sub(r"^[\s\-–—:•]+", "", DIST.sub(" ", line, count=1)).strip()
        paren = re.fullmatch(r"\((.+)\)", rest)
        if paren:
            rest = paren.group(1).strip()
        if VACANT.search(rest):
            vacant.add(d)
            continue
        if _reads_as_name(rest):
            out[d] = clean(rest)
            continue
        if rest:
            continue                    # the line says something else — never look past it
        nxt = lines[i + 1] if i + 1 < len(lines) else ""
        if DIST.search(nxt):
            continue                    # the next district's line: stop, never borrow
        if VACANT.search(nxt):
            vacant.add(d)
        elif _reads_as_name(nxt):
            out[d] = clean(nxt)
    return out, vacant
# --- the fifth shape: a STRUCTURED BLOCK PER OFFICIAL -------------------------
# The four readings above all guess at DISTANCE: they find a district number
# and reach outward for the nearest thing that reads like a name. That is what
# a page written as prose or as a list forces, and every one of this file's
# pinned directions exists because reaching outward can reach into the next
# person's row.
#
# Green Lake does not force it. Its officials pages publish one self-contained
# block per person, each carrying its own name, its own title, its own district
# and its own contact:
#
#     <div class="indexRoll grid-row">
#       <h2 class="indexRoll__head">Nancy Hoffmann</h2>
#       <p class="indexRoll__sub">County Board Supervisor</p>
#       <ul class="metaList"><li><span>District:</span> 1</li>
#                            <li><span>District Area:</span> Village of ...</li></ul>
#       <ul class="addrList"><li>N786 County Road H</li> ... </ul>
#     </div>
#
# So nothing is inferred from adjacency: a field belongs to the person whose
# block it sits in, and a reading direction cannot shift.
#
# WHY IT WAS RECORDED AS PUBLISHING NOTHING, MEASURED RATHER THAN GUESSED AT.
# `DIST` needs the literal word "district" beside the number; this page writes
# it as "<span>District:</span> 1", and `_BREAK` splits on `</span>`, so the
# word and the number land on DIFFERENT LINES. All three word-based readings
# and both strict variants therefore see a page with zero districts on it.
# `column-before` DOES NOT: run against this page today it resolves all
# nineteen — seventeen names and the two seats the county marks vacant. THE
# READER THIS COUNTY NEEDED HAS BEEN IN THIS FILE SINCE 2026-08-27 AND NOBODY
# POINTED IT AT GREEN LAKE, which makes the gap record a sweep that was not
# re-run rather than a county that publishes nothing — Trempealeau's lesson,
# a second time. (`column-after`, the same reader pinned the other way, finds
# 2 of 19 and files the person BELOW each vacant seat into it; it fails the
# count gate loudly, which is what that gate is for.)
#
# The structured reading still ships instead, because the column reading pairs
# by adjacency and can only ever yield a NAME: the chairman's role, the county
# e-mail and the phone all sit in the block and none of them sits at a fixed
# distance. ASK WHETHER A PAGE IS STRUCTURED BEFORE ASKING WHICH DIRECTION TO
# READ IT IN — and when a new page shape defeats the readings, RE-RUN THE
# EXISTING ONES OVER THE COUNTIES ALREADY WRITTEN OFF.
#
# THE HOME ADDRESSES ARE DELIBERATELY NOT CARRIED. Each supervisor's block
# publishes their house ("N786 County Road H, Dalton"); the fleet's standing
# rule is that a home address never ships even where the source publishes it
# (the same call Taylor's document roster records). The county e-mail and the
# phone printed beside it are official contact details and do.
INDEXROLL_BLOCK = re.compile(
    r'(?s)<div class="indexRoll[ "].*?(?=<div class="indexRoll[ "]|</article>)')
INDEXROLL_HEAD = re.compile(r'(?is)<h2[^>]*class="indexRoll__head"[^>]*>(.*?)</h2>')
INDEXROLL_SUB = re.compile(r'(?is)<p[^>]*class="indexRoll__sub"[^>]*>(.*?)</p>')
INDEXROLL_DIST = re.compile(r'(?is)<li>\s*<span>\s*District:\s*</span>\s*(\d{1,2})\s*</li>')
INDEXROLL_ADDR = re.compile(r'(?is)<ul[^>]*class="addrList"[^>]*>(.*?)</ul>')
# The county's markup gives these anchors a bare value rather than a tel:/mailto:
# scheme, so they are read as the text they are.
PHONE = re.compile(r"\d{3}[.\s-]\d{3}[.\s-]\d{4}")
EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
# "County Board Chairman" — the role sits in the block's own subtitle, which is
# why this county needs no `attach_officer_roles` pass. "County Board
# Supervisor" is the office, not a role, and matches nothing here.
SUB_ROLE = re.compile(
    r"(?i)\b((?:1st|2nd|first|second)\s+)?(vice[\s-]?)?chair(?:man|person|woman)?\b")


def _strip_tags(fragment):
    return " ".join(html_lib.unescape(_TAG.sub(" ", fragment)).split())


def _indexroll(page_html, seats):
    """District -> (name, role, email, phone) read from each person's own block."""
    found, vacant, contacts = {}, set(), {}
    for block in INDEXROLL_BLOCK.findall(page_html):
        head = INDEXROLL_HEAD.search(block)
        dist = INDEXROLL_DIST.search(block)
        if not head or not dist:
            continue
        d = int(dist.group(1))
        if not (1 <= d <= seats) or d in found or d in vacant:
            continue
        name = _strip_tags(head.group(1))
        if VACANT.search(name):
            vacant.add(d)                   # the county says the seat is empty
            continue
        if not is_name(name):
            continue
        sub = INDEXROLL_SUB.search(block)
        role = None
        if sub:
            m = SUB_ROLE.search(_strip_tags(sub.group(1)))
            if m:
                role = role_case(m.group(0))
        found[d] = (clean(name)[0], role)
        addr = INDEXROLL_ADDR.search(block)
        if addr:
            text = _strip_tags(addr.group(1))
            row = {}
            phones = PHONE.findall(text)
            if phones:
                row["phone"] = phones[0]
                if len(phones) > 1:
                    # Harley Reabe's block prints a landline and a cell in one
                    # anchor. The first ships; the rest are named, not dropped
                    # silently, so a second number never becomes an invisible loss.
                    print("  note Green Lake  district %d publishes %d numbers "
                          "(%s) — the first ships" % (d, len(phones), ", ".join(phones)),
                          file=sys.stderr)
            email = EMAIL.search(text)
            if email:
                row["email"] = email.group(0)
            if row:
                contacts[d] = row
    # AN ADDRESS ON TWO DISTRICTS IS NOT A PERSONAL ADDRESS. Measured
    # 2026-08-29: bhutchison@greenlakecountywi.gov is printed as the contact
    # for districts 13, 17 and 18 (Don Lenz, Robert Grim, Sara Allen) — three
    # different people, and a local part matching none of their names nor any
    # official the county's own site names anywhere. Shipping it would give a
    # reader the wrong person's inbox in the name of the one they looked up,
    # so it ships for none of them and the measurement prints every run.
    by_addr = {}
    for d, row in contacts.items():
        if row.get("email"):
            by_addr.setdefault(row["email"].lower(), []).append(d)
    for addr, ds in sorted(by_addr.items()):
        if len(ds) > 1:
            for d in ds:
                contacts[d].pop("email", None)
            print("  note Green Lake  %s is published for %d districts (%s) — "
                  "not a personal address, dropped from all"
                  % (addr, len(ds), ", ".join(str(x) for x in sorted(ds))),
                  file=sys.stderr)
    return found, vacant, contacts
# --- the fielded reading: a page that LABELS its own fields -------------------
# SAUK IS THE ONE COUNTY WITH NO READING DIRECTION TO PIN, because its page
# does not put a name NEAR a district — it puts one in a field whose own label
# says "Supervisor:". Everything the rest of this file pins per county exists
# to survive that ambiguity; here it does not arise, and a page tweak cannot
# silently flip a reading that keys off the page's own words.
#
# The county runs an IBM Domino/XPages application whose per-district panel is
# a heading ("DISTRICT #4") followed by the district's WARD COMPOSITION, then
# labelled Supervisor / Phone / Email / Address rows. The generic readings are
# blind to it in both directions: `is_name` rejects the "Supervisor: ..." line
# on the word supervisor, and rejects every ward line on town/city/village/ward
# — so all three windowed readings resolve ZERO of the thirty-one seats. That
# is a reader limit, not a publisher gap, and it is exactly the shape the
# 2026-08-27 re-sweep found nine counties sitting in.
PANEL_HEAD = re.compile(r"(?i)^district\s*#\s*(\d{1,2})$")
FIELD = re.compile(r"(?i)^(supervisor|phone|email)\s*:\s*(.+)$")
# The application has a template of its own for an empty seat — the panel
# renders a `NoSupervisorPanel` reading "There is no supervisor for this
# District." — so a vacancy here is the county's own statement, not an absence
# this reader inferred. `VACANT` cannot see it: the sentence never says vacant.
NO_SUPERVISOR = re.compile(r"(?i)\bno supervisor for this\s+district\b")
# Ward lines, the witness input: "Village Of Lake Delton Wards 1, 2, 3 and 7",
# "Town of Baraboo, Ward 4", "Town of Dellona, Ward 1 and Ward 2".
WARD_LINE = re.compile(r"(?i)^(town|city|village)\s+of\s+(.+?)[,\s]+wards?\s+(.+)$")


def flip_last_first(text):
    """"Deitrich, John M." -> "John M. Deitrich", punctuation as published.

    `clean` would do the flip and also strip the trailing period off a middle
    initial — its end-strip runs before the comma split, which is why the
    counties already shipping carry names like "Terry M Spencer". Those bytes
    are not re-litigated here; this reading keeps what the county printed.
    """
    text = " ".join(text.split())
    if "," not in text:
        return text
    a, b = [x.strip() for x in text.split(",", 1)]
    if SUFFIX.match(b):
        return "%s %s" % (a, b)     # "Schaefer, II" is a suffix, never a flip
    return "%s %s" % (b, a)


# --- Calumet: a district per TABLE CELL, and a role the page contradicts ------
#
# calumetcounty.org/243/County-Board-of-Supervisors is a CivicPlus page whose 21
# seats sit in four TABS ("Districts 1-6", "7-12", "13-18", "19-21"). The tabs
# are client-side, so one fetch carries all four panels, and each district is a
# self-contained <td>: its heading, the member, their wards, the year they were
# seated, a home address, a phone and their committees. THE CELL BOUNDARY IS THE
# GUARD — the reason this county needs a reader of its own rather than one of the
# line readings. A district whose name went missing could otherwise reach down
# into its neighbour's block, which is the failure `-strict` was added for; here
# it cannot, because the read never leaves the cell the heading opened.
#
# THE ADDRESSES ARE DELIBERATELY NOT CARRIED. Every cell prints the supervisor's
# house ("2018 S. Jackson Street, Appleton"); the fleet's standing rule is that a
# home address never ships even where the source publishes it — the same call
# Taylor's document roster and Green Lake's block reader record.
#
# NO E-MAIL SHIPS EITHER, AND THAT IS A MEASUREMENT RATHER THAN A GAP IN THIS
# READER: the county publishes no supervisor mailbox anywhere on the page. Each
# "Email <name>" link is a CivicPlus FormCenter contact FORM
# (/FormCenter/County-Supervisors-6/Contact-District-1-Supervisor-...), one per
# district. It is not carried as `url` either, because the card renders that
# field as "Supervisor page" and a contact form is not one — mislabelling the
# link would cost a reader more than the missing link does, and the phone this
# reader does carry reaches every one of the 21.
#
# TWO SUPERVISORS ARE LABELLED "Vice-Chairperson" AND ONLY ONE OF THEM IS, which
# is why `_calumet` returns its roles separately for the caller to gate rather
# than writing them straight onto the members. Measured 2026-08-31: the page
# gives District 4 (Budde) and District 19 (Dietrich) the same role. The county's
# own organisational minutes of 21 April 2026 settle it — item 8 elected Connors
# chair, item 11 elected Budde vice-chair after Dietrich WITHDREW his nomination,
# and item 12 made Schwalenberg 2nd vice-chair — so District 19 carries a label
# from the term before, which nobody took down.
#
# THE FIX IS A UNIQUENESS GATE, NOT A PINNED NAME. Writing "Budde is the vice
# chair" into this file would be correct today and would go stale in April 2028
# exactly as the county's page did; the gate instead drops any role two
# supervisors claim, names the conflict on the run log, and ships the roles that
# are unambiguous. So Calumet ships a chair and a 2nd vice-chair today, and the
# vice-chair returns on its own — with no code change — the day the county takes
# the stale label down. A role guessed onto the wrong supervisor is worse than no
# role at all.
CAL_PANELS = re.compile(r'(?is)<div class="cpTabPanels">')
CAL_CELL = re.compile(r"(?is)<td\b[^>]*>(.*?)</td>")
CAL_DIST = re.compile(r"(?i)^district\s+(\d{1,2})\b")
# Longest form first: Calumet's "Second Vice-Chair" must not read as the plain
# "Vice-Chair" its two conflicting cells carry.
#
# THE SUFFIX IS OPTIONAL AND THAT COST A CHAIRMAN. Written as
# `chair(?:man|person|woman)` the last branch REQUIRES a suffix, which is true
# of Calumet ("Chairperson") and false of Buffalo, whose h5 reads a bare
# "Chair<br />District 11". Buffalo resolved 14 of 14 seats with its chairman
# silently unnamed and every guard green — the same shape as the role trap this
# gate exists for, one level down: a field that is not the seat passes every
# seat count in the file. `?` makes the suffix optional; the ordered alternation
# still gives "Vice Chair" to the vice-chair branch before the bare one.
STRUCTURED_ROLE = re.compile(r"(?i)\b((?:second|2nd|first|1st)\s+vice[\s\-]?chair(?:man|person|woman)?"
                             r"|vice[\s\-]?chair(?:man|person|woman)?"
                             r"|chair(?:man|person|woman)?)\b")
# The county writes its numbers five ways across the 21 cells — "(920) 639-6908",
# "920-574-0421", "Phone:(920) 850-7931" with no space, "( 217) 722-1974" with a
# space INSIDE the parenthesis, and District 15's "(920) 853-3440 Second
# Vice-Chair" with the role run onto the same line. Anchoring on the county's own
# "Phone:" label and rebuilding the number from its three groups reads all five;
# the module-level PHONE (Green Lake's) matches only the bare-dash form and would
# silently drop twenty of the twenty-one.
CAL_PHONE = re.compile(r"(?i)phone:?\s*\(?\s*(\d{3})\s*\)?[\s.\-]*(\d{3})[\s.\-]*(\d{4})")
CAL_NICK = re.compile(r"\s*\([^)]*\)\s*")


# Shared by the structured readers below: Calumet's table cell and Buffalo's
# heading pair both need a fragment's own <br>-separated fields kept apart.
def _flat_lines(fragment):
    """A markup fragment's own lines, keeping its <br>-separated fields apart."""
    h = re.sub(r"(?is)<br\s*/?>", "\n", fragment)
    h = re.sub(r"(?is)</(p|h\d|div|li|tr)>", "\n", h)
    h = _TAG.sub(" ", h)
    return [" ".join(l.split()) for l in html_lib.unescape(h).split("\n") if l.strip()]


def _calumet(page_html, seats):
    """district -> (name, None), the seats the page empties, phones, and roles."""
    m = CAL_PANELS.search(page_html)
    region = page_html[m.end():] if m else page_html
    found, vacant, contacts, roles = {}, set(), {}, {}
    for fragment in CAL_CELL.findall(region):
        lines = _flat_lines(fragment)
        if len(lines) < 2:
            continue
        head = CAL_DIST.match(lines[0])
        if not head:
            continue
        d = int(head.group(1))
        if not (1 <= d <= seats) or d in found or d in vacant:
            continue
        name = lines[1]
        if VACANT.search(name):
            vacant.add(d)                   # the county says the seat is empty
            continue
        # `is_name` is a SHARED guard and is not widened for one county: it
        # rejects District 2's "Jacob (Jake) Wayne" on the parenthesis, and
        # widening it would loosen the name test for all fifty. So the name is
        # VALIDATED with the nickname removed and SHIPPED as the county spells
        # it. Without this the seat would not resolve and the all-seats-or-
        # nothing rule would correctly refuse the whole county for one bracket.
        if not is_name(CAL_NICK.sub(" ", name).strip()):
            continue
        found[d] = (name, None)
        text = " ".join(lines)
        role = STRUCTURED_ROLE.search(text)
        if role:
            roles[d] = role_case(role.group(1))
        phone = CAL_PHONE.search(text)
        if phone:
            contacts[d] = {"phone": "(%s) %s-%s" % phone.groups()}
    return found, vacant, contacts, roles


# SHARED BY EVERY STRUCTURED READER THAT TAKES A ROLE OFF THE PAGE IT READS.
# Calumet is why it exists — two districts labelled "Vice-Chairperson", only one
# of them current — and Buffalo is why it carries no county's name: Buffalo
# publishes exactly one Chair and one Vice Chair and passes this cleanly, which
# is what a gate looks like when the page is right. Keeping one helper means the
# next structured county inherits the guard instead of re-earning it.
def attach_unique_roles(roles, districts, county):
    """Write through only the roles exactly one supervisor claims."""
    holders = {}
    for d, role in roles.items():
        holders.setdefault(role, []).append(d)
    for role, ds in sorted(holders.items()):
        if len(ds) > 1:
            print("  note %-12s %r is on districts %s \u2014 the page cannot say which "
                  "holds it, so it ships on neither"
                  % (county, role, ", ".join(str(x) for x in sorted(ds))), file=sys.stderr)
            continue
        row = districts.get(str(ds[0]))
        if row and not row.get("vacant"):
            row["role"] = role
            print("  role %-12s district %d: %s -> %s"
                  % (county, ds[0], row["name"], role), file=sys.stderr)
    return districts


# --- Buffalo: an Elementor heading pair per supervisor -------------------------
#
# buffalocountywi.gov/government/boards-committees/county-board/ is a WordPress
# /Elementor page that gives every supervisor a container holding an <h4> with
# the name and an <h5> with the district — and, for the two officers, the role
# on its own line INSIDE that same <h5>, split from the district by a <br>:
#
#     <h4>Max Weiss</h4>
#     <h5>Vice Chair<br /> District 7 (Town of Modena, Alma, and Gilmanton)</h5>
#
# READ AS HEADINGS, NOT AS LINES, and the reason is the page's size rather than
# its shape. The document is 612 KB because it also carries the county's whole
# agenda-and-minutes archive — several hundred committee PDFs, each a dated
# link — so a flattened line reading would be scanning a haystack for fourteen
# needles. Pairing <h4> with the <h5> under it never leaves a member's own
# container, which is the same guard `_calumet`'s table cell gives.
#
# THE E-MAILS ARE CLOUDFLARE-OBFUSCATED, WHICH IS THE BROWN COUNTY (IL) TRAP
# EXACTLY: no `mailto:` survives in the markup, so a parser that looks for one
# returns fourteen supervisors carrying nothing and every count guard stays
# green. Here the token sits in the href FRAGMENT
# (/cdn-cgi/l/email-protection#<hex>) rather than in Manitowoc's `data-cfemail`
# attribute — same encoding, different carrier — and `cf_decode` reads it. There
# is no second scramble layer, unlike Manitowoc. As everywhere in this fleet,
# obfuscation markup that decodes to NOTHING is a hard failure rather than a
# quietly empty column; see EMAIL_MIN below.
#
# TWO OF THE FOURTEEN PUBLISH NO E-MAIL AT ALL and that is the county's doing,
# not this reader's: districts 8 and 14 have no "Email" link on the page. An
# absent field renders nothing rather than a placeholder, so those two cards
# name their supervisor and stop.
#
# THE COUNTY USES TWO MAIL DOMAINS AND BOTH SHIP AS PUBLISHED. Nine addresses
# are on buffalocountywi.gov and four on co.buffalo.wi.us, which reads like a
# half-finished migration; both domains resolve, both are the county's own, and
# rewriting somebody's contact detail to make a column tidy is not this
# project's call. `EMAIL_DOMAINS` gates them so a THIRD domain — the shape a
# hijacked or mistyped address would take — fails the county loudly.
#
# NELSON IS A SURNAME AND A PLACE IN THIS COUNTY, which matters to anyone
# corroborating this roster against the county's minutes rather than to the
# reader below: districts 3 and 6 are Steve Nelson and Nathan Nelson, and
# district 1 is "Town of Nelson and Village of Nelson". A surname is not a key
# here (the Vermilion lesson) and a bare name search hits the townships too.
BUF_H4 = re.compile(r"(?is)<h4[^>]*>(.*?)</h4>")
BUF_H5 = re.compile(r"(?is)<h5[^>]*>(.*?)</h5>")
BUF_DIST = re.compile(r"(?i)^district\s+(\d{1,2})\b")
BUF_MAIL = re.compile(r"/cdn-cgi/l/email-protection#([0-9a-fA-F]{6,})")
# The county's own two domains, pinned: see the note above.
EMAIL_DOMAINS = frozenset(("buffalocountywi.gov", "co.buffalo.wi.us"))
EMAIL_MIN = 10          # 12 of 14 publish one; districts 8 and 14 do not


def _heading_block(page_html, seats):
    """district -> (name, None), emptied seats, contacts, roles — from <h4>/<h5>."""
    found, vacant, contacts, roles = {}, set(), {}, {}
    starts = [m.start() for m in BUF_H4.finditer(page_html)]
    for i, start in enumerate(starts):
        block = page_html[start: starts[i + 1] if i + 1 < len(starts) else len(page_html)]
        head, sub = BUF_H4.search(block), BUF_H5.search(block)
        if not head or not sub:
            continue
        lines = _flat_lines(sub.group(1))
        district = [l for l in lines if BUF_DIST.match(l)]
        if not district:
            continue                        # an <h4> that heads something else
        d = int(BUF_DIST.match(district[0]).group(1))
        if not (1 <= d <= seats) or d in found or d in vacant:
            continue
        name = " ".join(_flat_lines(head.group(1)))
        if VACANT.search(name) or any(VACANT.search(l) for l in lines):
            vacant.add(d)                   # the county says the seat is empty
            continue
        if not is_name(name):
            continue
        found[d] = (clean(name)[0], None)
        # anything in the <h5> that is not the district line is the role
        for line in lines:
            if BUF_DIST.match(line):
                continue
            m = STRUCTURED_ROLE.search(line)
            if m:
                roles[d] = role_case(m.group(1))
        token = BUF_MAIL.search(block)
        if token:
            address = cf_decode(token.group(1))
            # The domain is compared EXACTLY, not with endswith: a suffix test
            # accepts "…@not-buffalocountywi.gov" as readily as the county's own.
            domain = address.rsplit("@", 1)[-1].lower()
            if EMAIL_SHAPE.match(address) and domain in EMAIL_DOMAINS:
                contacts[d] = {"email": address}
    return found, vacant, contacts, roles


def _fielded(lines):
    """district -> {name, role, email, phone}, plus the seats the page empties."""
    heads = []
    for i, line in enumerate(lines):
        m = PANEL_HEAD.match(line)
        if m:
            heads.append((i, int(m.group(1))))
    seen = [d for _, d in heads]
    if len(set(seen)) != len(seen):
        dupes = sorted({d for d in seen if seen.count(d) > 1})
        raise RuntimeError("the page carries two panels for district(s) %s — a "
                           "later one would silently overwrite an earlier" % dupes)
    found, vacant, wards = {}, set(), {}
    for k, (i, d) in enumerate(heads):
        j = heads[k + 1][0] if k + 1 < len(heads) else len(lines)
        panel = lines[i + 1:j]
        row = {"name": None, "role": None, "email": None, "phone": None}
        for line in panel:
            m = FIELD.match(line)
            if m:
                label, value = m.group(1).lower(), m.group(2).strip()
                if label == "supervisor" and row["name"] is None:
                    row["name"] = flip_last_first(value)
                elif label == "phone" and row["phone"] is None:
                    row["phone"] = value
                elif label == "email" and row["email"] is None:
                    row["email"] = value
                continue
            wm = WARD_LINE.match(line)
            if wm:
                ctv = {"town": "T", "city": "C", "village": "V"}[wm.group(1).lower()]
                mcd = re.sub(r"[^a-z]", "", wm.group(2).lower())
                for n in re.findall(r"\d+", wm.group(3)):
                    wards.setdefault(d, set()).add((ctv, mcd, int(n)))
        if row["name"]:
            found[d] = row
        elif NO_SUPERVISOR.search(" ".join(panel)):
            vacant.add(d)
        # a panel that is neither is left unresolved: the all-seats guard fails
    return found, vacant, wards
# --- the sixth shape: a real TABLE, read as rows --------------------------------
# Every reading above works on the page's LINES, which is what a list, a run of
# prose or a CMS's stack of divs leaves behind. Monroe leaves a table, and reading
# its lines is unsafe twice over: its ward cells run to six lines (past
# COLUMN_SPAN, so `_column` walks out of the row) and an events calendar above it
# prints seventy-odd bare numerals in the district range, each followed by a time
# and an event title — a month whose calendar named a person would seat that
# person.
#
# So the row is read as a row, and its columns are located BY HEADER NAME: a
# column reordered upstream cannot shift a roster, and a column renamed or
# dropped fails loudly instead of quietly reading the wrong cell. Each row states
# its district TWICE — the District cell, and the local part of the county e-mail
# address it publishes for that seat (district.07@co.monroe.wi.us) — and the two
# must agree, which is the same two-witnesses stance the pinned reading
# directions take, expressed in the data the county already maintains.
TABLE = re.compile(r"(?is)<table\b.*?</table>")
MONROE_COLUMNS = ("district", "supervisor", "email")
MONROE_EMAIL = re.compile(r"(?i)^district\.(\d{1,2})@co\.monroe\.wi\.us$")


def _monroe(page_html):
    """District -> (name, role), plus the county e-mail published per seat."""
    for table in TABLE.findall(page_html):
        rows = [[to_lines(cell) for _, cell in TABLE_CELL.findall(row)]
                for row in TABLE_ROW.findall(table)]
        header, body = None, []
        for i, cells in enumerate(rows):
            heads = [c[0].lower() if c else "" for c in cells]
            if all(want in heads for want in MONROE_COLUMNS):
                header = {name: j for j, name in enumerate(heads)}
                body = rows[i + 1:]
                break
        if header is None:
            continue
        found, vacant, contact = {}, set(), {}
        for cells in body:
            if len(cells) <= max(header.values()):
                continue
            key = cells[header["district"]]
            who = cells[header["supervisor"]]
            mail = cells[header["email"]]
            if not key or not (who or mail):
                continue                    # the table's own blank spacer row
            num = BARE_NUM.match(key[0].strip())
            if not num:
                raise RuntimeError("Monroe: district cell %r is not a number" % key[0])
            d = int(num.group(1))
            said = MONROE_EMAIL.match(mail[0]) if mail else None
            if not said or int(said.group(1)) != d:
                raise RuntimeError(
                    "Monroe: district %d's row publishes %r — the row's two "
                    "statements of its own district disagree, so the table has "
                    "reshaped; re-read it before shipping"
                    % (d, mail[0] if mail else None))
            if who and VACANT.search(who[0]):
                vacant.add(d)
                continue
            if not who or not is_name(who[0]):
                continue                    # the count guard names the seat
            found[d] = clean(who[0])
            contact[d] = {"email": mail[0].lower()}
        return found, vacant, contact
    raise RuntimeError("Monroe: no table on the page heads columns %s — the page "
                       "has changed shape" % (MONROE_COLUMNS,))
# --- the sixth shape: a bare number and a name on ONE line ---------------------
# Manitowoc writes `_column`'s table on one line per seat:
#
#     District Number    Name              (the header, said once)
#     1                  Lillibridge, James
#     2                  Wolf, Gregg
#
# `DIST` needs the word beside the number and `BARE_NUM` needs the numeral
# alone in its cell, so all five earlier readings are blind to it. BOTH halves
# are required here — a leading 1-2 digit number AND a remainder that reads as
# a name — because a bare number on its own matches half the footer of any
# county site ("1010 S. 8th Street" does not, but only by luck of the digit
# count, and `is_name` is what actually makes this safe).
#
# It reports its own vacancies for the same reason `_column` does: a page that
# never says "district" beside a seat is invisible to `vacant_districts`.
NUMBERED_LINE = re.compile(r"^#?\s*(\d{1,2})\s+(.+)$")


def _numbered_line(lines, seats):
    out, vacant = {}, set()
    for line in lines:
        m = NUMBERED_LINE.match(line.strip())
        if not m:
            continue
        d = int(m.group(1))
        rest = m.group(2).strip()
        if not (1 <= d <= seats) or d in out or d in vacant:
            continue
        if VACANT.search(rest):
            vacant.add(d)
        elif _reads_as_name(rest):
            out[d] = clean(rest)
    return out, vacant


READINGS = {
    "same-line": _same_line,
    "before": lambda ls: _windowed(ls, WINDOW_BEFORE),
    "after": lambda ls: _windowed(ls, WINDOW_AFTER),
}
# The readings that STOP at the next district line, and therefore report their
# own vacancies: the forward-only `vacant_districts` cannot see a vacancy the
# page prints on the side it is not scanning.
STRICT_READINGS = {
    "before-strict": lambda ls: _windowed_strict(ls, WINDOW_BEFORE),
    "after-strict": lambda ls: _windowed_strict(ls, WINDOW_AFTER),
    "same-line-lead": _same_line_lead,
    "same-line-or-next": _same_line_or_next,
}
COLUMN_READINGS = {"column-after": True, "column-before": False}


def vacant_districts(lines, seats, strategy="after"):
    """Districts the county itself marks empty, read from the district's OWN row.

    ON A `same-line` PAGE THE WINDOW IS THE LINE, and that is not a nicety.
    Marinette lists "Trygve Rhude - District 22", then his wards, then the
    next row — which is its unnumbered "VACANT SEAT". A three-line lookahead
    reached across the row boundary (the ward line in between says nothing
    about a district, so stopping at the next district heading does not help)
    and filed District 22 as vacant, ERASING A SITTING SUPERVISOR — silently,
    because the seat count still came to 30 and every guard stayed green.
    A page that puts name and district on one line states a vacancy there too.
    For the other readings the window survives, now stopping at the next
    district line. Measured 2026-08-29 while adding Marinette.
    """
    out = set()
    for i, line in enumerate(lines):
        m = DIST.search(line)
        if not m:
            continue
        d = int(m.group(1))
        if not (1 <= d <= seats):
            continue
        window = [line]
        if strategy != "same-line":
            # a page that puts the name on its own line may put the vacancy
            # there too; one that puts both on the district line never does
            for j in range(i + 1, min(i + 3, len(lines))):
                if DIST.search(lines[j]):
                    break           # the next district's row: never borrow it
                window.append(lines[j])
        if VACANT.search(" ".join(window)):
            out.add(d)
    return out


def fetch_bytes(url, headers=None, timeout=45, attempts=4, allow_lax_tls=True):
    """Raw bytes plus THE URL THAT ANSWERED, which is not always the one asked.

    Kenosha's directory is addressed by a stable county page id that 302s to
    whichever DocumentCenter edition is current; returning the resolved URL is
    what lets the run log name the edition it actually read.

    429 IS RATE LIMITING AND NOT A REFUSAL, and this file had no answer for it:
    Winnebago's Cloudflare front rate-limits by address, so two runs close
    together dropped its 36 seats out of the roster entirely for that run — a
    county vanishing from the shipped file because of pacing, which reads on
    the weekly PR exactly like a county whose page reshaped. 429 and 5xx are
    therefore waited out (a numeric Retry-After is honoured, capped, so a
    hostile value cannot hang CI); 403 and 404 are not, because a refusal or a
    moved page is not fixed by waiting.
    """
    lax = ssl.create_default_context()
    lax.check_hostname = False
    lax.verify_mode = ssl.CERT_NONE
    # The caller's choice wins; headers_for decides only when it made none.
    # Until 2026-09-12 this line read `headers = HONEST_UA if host in
    # HONEST_UA_HOSTS else UA`, which discarded the argument — see the note
    # beside TOKEN_REFUSED_HOSTS for the two things that cost.
    headers = headers or headers_for(url)
    last = None
    for attempt in range(attempts):
        for ctx in (None, lax):
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
                    body = r.read()
                    # urllib never unwraps gzip. Both header sets ask for
                    # identity today and ARCHIVE_UA asks for nothing, so this is
                    # for a server that compresses anyway — and for the next
                    # header set that asks, which is how it got here.
                    if (r.headers.get("Content-Encoding") or "").lower() == "gzip":
                        body = gzip.decompress(body)
                    return body, r.geturl()
            except urllib.error.HTTPError as e:
                last = e
                if e.code == 429 or e.code >= 500:
                    break           # a wait fixes this; a second TLS context cannot
            except Exception as e:  # noqa: BLE001 - reachability probe
                last = e
        waitable = isinstance(last, urllib.error.HTTPError) and (
            last.code == 429 or last.code >= 500)
        if not waitable or attempt == attempts - 1:
            break
        after = (last.headers.get("Retry-After") or "").strip()
        delay = min(float(after), 30.0) if after.isdigit() else 5.0 * 3 ** attempt
        print("  wait HTTP %d from %s — retrying in %.0fs"
              % (last.code, url, delay), file=sys.stderr)
        time.sleep(delay)
    raise RuntimeError("could not fetch %s (%s)" % (url, last))


# --- the archive ladder ------------------------------------------------------
# For the counties in ARCHIVE_READ only: their own host refuses this client on
# every path and header, and the Internet Archive holds the page they refuse to
# hand over. See the docstring for why that is a network refusal rather than
# something to fix in the request, for the two rules below, and for why this is
# a FETCH and never the document route DOCUMENT_ROSTERS carries.
CDX = ("https://web.archive.org/cdx/search/cdx?url=%s&output=json"
       "&fl=timestamp,statuscode&filter=statuscode:200&limit=-10")
SNAPSHOT = "https://web.archive.org/web/%sid_/%s"     # id_ = the original bytes
# THE ARCHIVE IS ASKED AS THIS PROJECT, NOT AS A BROWSER, and that is load
# bearing rather than manners: web.archive.org answers its own "Temporarily
# Offline" page with HTTP 503 to the shared Chrome user-agent `UA` carries,
# and 200 to a client that says who it is (measured 2026-08-29 — the same
# capture, same second, 503 as Chrome and 200 as anything named). `UA` exists
# for county CMSs that refuse non-browser clients; it is the wrong header
# here, and sending it reads as an outage that is not one.
#
# THAT WAS TRUE AND UNENFORCED FROM 2026-08-29 TO 2026-09-12: fetch_archived
# passed this dict and fetch_bytes overwrote it with `UA`, so every archive
# read went out as the client the archive was measured refusing. See the note
# beside TOKEN_REFUSED_HOSTS.
ARCHIVE_UA = {"User-Agent": "districtry-county-board-scraper/1.0 "
                            "(+https://districtry.com; civic boundary data)"}


def board_seated_on(today=None):
    """The date the sitting county board took office.

    Wis. Stat. 59.10(3)(d): supervisors are "elected for 2-year terms at the
    election to be held on the first Tuesday in April in even-numbered years"
    and "take office on the 3rd Tuesday in April of that year". So a page
    describes the board that sits NOW only if it is at least as new as that
    date — which is what makes this a usable guard on an archived capture
    rather than an arbitrary age limit.
    """
    today = today or datetime.date.today()
    year = today.year if today.year % 2 == 0 else today.year - 1
    while True:
        seated = datetime.date(year, 4, 15)
        seated += datetime.timedelta(days=(1 - seated.weekday()) % 7)   # 3rd Tue
        if seated <= today:
            return seated
        year -= 2               # April of this even year has not happened yet


assert board_seated_on(datetime.date(2026, 8, 29)) == datetime.date(2026, 4, 21)
assert board_seated_on(datetime.date(2026, 4, 20)) == datetime.date(2024, 4, 16)
assert board_seated_on(datetime.date(2025, 1, 1)) == datetime.date(2024, 4, 16)


def _archive_json(url, tries=5):
    """The Archive answers 503 while it is down; back off rather than give up."""
    last = None
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers=ARCHIVE_UA)
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except Exception as e:      # noqa: BLE001 - reachability, retried below
            last = e
            time.sleep(5 * (attempt + 1))
    raise RuntimeError("the Internet Archive did not answer %s (%s)" % (url, last))



def fetch_or_archive(url, fips, county, headers=None):
    """(page html, how it was read). LIVE FIRST, ALWAYS — a county that stops
    refusing this client starts reading live with no code change, and the run
    log says which rung answered either way."""
    try:
        return fetch(url, headers), "live"
    except Exception as live_error:     # noqa: BLE001 - the refusal is the point
        if fips not in ARCHIVE_READ:
            raise
        page, stamp = fetch_archived(url)
        print("  note %-12s live read refused (%s); read the Internet Archive "
              "capture of %s-%s-%s instead"
              % (county, live_error, stamp[:4], stamp[4:6], stamp[6:8]),
              file=sys.stderr)
        return page, "archive:" + stamp
def fetch(url, headers=None, timeout=45, attempts=4, allow_lax_tls=True):
    return fetch_bytes(url, headers, timeout, attempts,
                       allow_lax_tls)[0].decode("utf-8", "replace")


# COUNTIES WHOSE ROSTER RIDES THEIR OWN ARCGIS LAYER, NOT A PAGE. The
# "blocked county SITE is not a blocked county" lesson, applied at home:
# county.milwaukee.gov and racinecounty.com both refuse automated clients
# (a Cloudflare challenge and an Akamai deny — the county-officials gap
# record carries the measurements), and both counties turned out to publish
# their board ON THEIR OWN GIS instead, supervisor names as attributes on
# the district features. Currency is measured, not assumed: Milwaukee's
# layer was data-edited 2026-06-29 and Racine's 2026-04-23 — both after the
# April 2026 spring election that reseated every board — and Milwaukee is
# additionally WITNESSED on every run against the county's own Legistar web
# API (body 138, "Milwaukee County Board of Supervisors"): the layer's name
# set and Legistar's current-office set must agree exactly, or the county
# fails loudly. Legistar is a witness and never a source — its OData date
# filter is silently ignored server-side (filter client-side) and its end
# dates can be aspirational.
#
# OUTAGAMIE USED TO BE EXCLUDED HERE, on the grounds that outagamie.gov
# "answered one probe on 2026-08-25 and refused every later one (HTTP 403
# across UAs)" and that a roster this client cannot re-verify weekly does not
# ship. The reachability half of that was wrong and the shipping rule was
# right: the 403s were the edge refusing this scraper's SPOOFED BROWSER UA,
# the county serves the page to an honest one, and Outagamie now rides
# COUNTIES like any other weekly page (the docstring carries the whole
# measurement). It needs no GIS layer.
ARCGIS_COUNTIES = [
    {
        "fips": "55079", "name": "Milwaukee", "seats": 18,
        "layer": ("https://services2.arcgis.com/s1wgJQKbKJihhhaT/arcgis/rest/"
                   "services/Milwaukee_County_Supervisory_Districts/FeatureServer/46"),
        "fields": {"district": "District_Nbr", "name": "Sup_Name",
                    "email": "Email_Addr", "url": "Website_Url"},
        "source_url": ("https://services2.arcgis.com/s1wgJQKbKJihhhaT/arcgis/rest/"
                        "services/Milwaukee_County_Supervisory_Districts/FeatureServer/46"),
        "witness": {"client": "milwaukeecounty", "body_id": 138},
    },
    # LINCOLN (2026-09-02) — THE ENCLAVE THAT WAS NEVER A BLOCKED COUNTY.
    # www.co.lincoln.wi.us sits behind a Cloudflare MANAGED challenge
    # (`cf-mitigated: challenge`, not the flat Akamai deny this file records
    # elsewhere) and refuses every client here, /media/<id> documents included.
    # Its robots.txt answers 200 and permits them; the challenge is what
    # refuses. THE COUNTY IS NOT ITS WEBSITE: maps.co.lincoln.wi.us is a
    # second host on a different address, off the Cloudflare edge, running a
    # public ArcGIS Server whose WebMerc_Admin service is titled
    # "Administrative Layers for Lincoln County WI" and whose layer 5 is
    # Supervisor Districts — with SupervisorName and SupervisorPhone on every
    # one of the 22. Its ROOT is a stock IIS splash, the hollow-page class
    # build_wi_county_board_directory.py already records, which is why a
    # status sweep would have called the host nothing.
    #
    # A SECOND PUBLISHER AGREES ON THE PEOPLE: the Blue Book (April 2025)
    # gives Lincoln 22 seats and names Jesse Boyd its board chair; the layer
    # has 22 districts and its district 10 is Jesse Boyd. That is what rules
    # out the Coles case — a layer whose roster column is a stale snapshot.
    #
    # AND ONE SEAT IS WITHHELD BECAUSE THE TWO PUBLISHERS DRAW IT DIFFERENTLY.
    # See district_geometry_witness(): Town of Merrill ward 2 is district 21
    # in LTSB's filing and district 9 on the county's own map. The card reads
    # the reader's district from LTSB's geometry, so on that ground it would
    # name district 21's supervisor while the county says the seat is
    # district 9's. Twenty-one seats ship; that one names nobody and says why.
    {
        "fips": "55069", "name": "Lincoln", "seats": 22,
        "layer": ("https://maps.co.lincoln.wi.us/arcgis/rest/services/"
                  "WebMerc_Admin/MapServer/5"),
        "fields": {"district": "SuperID_Numeric", "name": "SupervisorName",
                   "phone": "SupervisorPhone", "url": "SuperIDLink"},
        "source_url": ("https://maps.co.lincoln.wi.us/arcgis/rest/services/"
                       "WebMerc_Admin/MapServer/5"),
        "district_witness": (
            "The county's own map and the state's filing put this district's "
            "boundary in different places, so which supervisor represents part "
            "of this ground is not settled and no name is shown."),
    },
    {
        "fips": "55101", "name": "Racine", "seats": 21,
        "layer": ("https://services1.arcgis.com/z1oAk3W6cWVD8swZ/arcgis/rest/"
                   "services/County_Board_of_Supervisors_WFL1/FeatureServer/0"),
        "fields": {"district": "DISTRICTID", "name": "REPNAME", "email": "Contact"},
        "source_url": ("https://services1.arcgis.com/z1oAk3W6cWVD8swZ/arcgis/rest/"
                        "services/County_Board_of_Supervisors_WFL1/FeatureServer/0"),
    },
]


# COUNTIES WHOSE ROSTER RIDES A DOCUMENT, NOT A FETCH. Illinois's
# il_county_commissioners_scraper.py carries Edwards and Wabash this way, for
# the same reason: the county publishes the list and nothing here can read it,
# so pretending a weekly check happens would be the lie. Each run prints a NOT
# RE-READ line naming the source and its age instead.
#
# TAYLOR (2026-08-29). co.taylor.wi.us publishes a district-keyed County Board
# directory at /directory/county-board/ — name, county e-mail, street address
# and phone for all seventeen districts, richer than most counties that ship.
# Every path on that host answers HTTP 202 with a 196-byte meta-refresh to
# `/.well-known/sgcaptcha/`; a captcha is an access control and is not defeated
# here, and the three other Taylor hosts tried do not resolve at all. The
# contents below were read from that page by the OPERATOR in an ordinary
# browser and handed over — a human reading a public page is the route the
# challenge permits, and it is why this is a document and not a scrape.
#
# THE STREET ADDRESSES ARE DELIBERATELY NOT CARRIED. They are supervisors'
# homes (rural routes, "W5895 Jolly Ave."), and this fleet's standing rule is
# that a home address never ships even when the source publishes it; a
# supervisor's house is not an office location. Name, county e-mail and phone
# are official contact details and do.
DOCUMENT_ROSTERS = [
    # ==== THE FIVE COUNTIES STOPPED ON 2026-08-31 BY THEIR OWN robots.txt ====
    #
    # Jackson, Richland, Rusk, Polk and Dunn were scraped weekly from their own
    # board pages, and every one of those hosts publishes:
    #
    #     User-agent: *
    #     Disallow: /
    #
    # naming half a dozen search engines above it and giving each a narrow
    # /admin/ and /manager/. This project's clients are none of them, so all
    # five sites were disallowed to it the whole time. The sweep that found
    # them is `wi/scripts/validate_robots.py`, written the same day and run
    # monthly, so this cannot recur quietly; the file's own COUNTIES note about
    # Iowa and Waushara turned entirely on the `*` group PERMITTING the board
    # path, and nothing had ever checked the other direction. THAT GUARD ALSO
    # CAUGHT THE COUNT: the first pass carried four and the fifth, Dunn, was
    # only found because the check was run again afterwards.
    #
    # THE CRAWL STOPS AND THE NAMES STAY. Removing them would blank 103 seats a
    # reader can see today, and robots.txt governs RETRIEVAL rather than what
    # already-public information may be shown: what these counties asked is
    # that automated clients stop fetching, which is what stopping the fetch
    # does. So each carries the roster as last read, dated 2026-08-31, with no
    # `live` key, and its card says the county ASKED — the same treatment
    # Pepin got when it was found the same day, and the reason its `why` exists.
    # These rows will age, visibly, and that is the honest cost of the choice.
    #
    # WHAT IT WOULD TAKE TO MAKE THEM WEEKLY AGAIN: the county's own say-so.
    # That is a letter, not a user-agent string, and nothing here will quietly
    # rename a client to get past a file that says no.
    {
        # ASHLAND, 2026-09-02 — the seventh, and the first found BEFORE it was
        # ever scheduled rather than after weeks of weekly runs. The reader that
        # produced these rows is scrape_ashland_board() above, kept for the day
        # the county says yes; the ward witness it ran scored 29 of the 30 wards
        # the page names in LTSB's same-numbered district, the thirtieth being
        # City of Ashland ward 18, which the county puts in District 11 and the
        # state files in District 8.
        "fips": "55003", "name": "Ashland", "seats": 21,
        "read_on": "2026-09-02",
        "source_url": "https://ashlandcountywi.gov/bos",
        "how": "read once from the county's own board page; its robots.txt "
               "disallows the whole site to every agent it does not name, so "
               "this roster is never re-fetched",
        "why": "The county asks automated readers not to crawl its site, so "
               "this name is a dated capture rather than the weekly re-read "
               "the other named counties get.",
        "roles": {"5": "Vice Chair", "21": "Chair"},
        # district -> (name, e-mail, phone); district 1 publishes
        # "Phone: Confidential" and ships with none
        "members": {
            "1": ('Elizabeth Gehred', 'elizabeth.gehred@ashlandcountywi.gov', None),
            "2": ('Thomas D. Trudeau', 'thomas.trudeau@ashlandcountywi.gov', '715-209-3920'),
            "3": ('Laura L. Nagro', 'laura.nagro@ashlandcountywi.gov', '715-216-1886'),
            "4": ('William Metzinger', 'william.metzinger@ashlandcountywi.gov', '715-682-5942'),
            "5": ('Clarence Campbell', 'clarence.campbell@ashlandcountywi.gov', '715-292-1160'),
            "6": ('Bradley Ray', 'bradley.ray@ashlandcountywi.gov', '715-513-6067'),
            "7": ('(Donald) Patrick Kinney', 'patrick.kinney@ashlandcountywi.gov', '715-682-9198'),
            "8": ('Richard Pufall', 'richard.pufall@ashlandcountywi.gov', '715-682-6116'),
            "9": ('Elizabeth A. Franek', 'elizabeth.franek@ashlandcountywi.gov', '715-969-6732'),
            "10": ('Paul Wilharm', 'paul.wilharm@ashlandcountywi.gov', '612-685-0445'),
            "11": ('Ronald Sztyndor', 'ronald.sztyndor@ashlandcountywi.gov', '845-517-7725'),
            "12": ('Benjamen Connors Sr.', 'benjamen.connors@ashlandcountywi.gov', '715-292-1728'),
            "13": ('Philip Livingston', 'philip.livingston@ashlandcountywi.gov', '715-292-5339'),
            "14": ('George E. Bussey', 'george.bussey@ashlandcountywi.gov', '715-209-2508'),
            "15": ('Marques Jolma', 'philip.livingston@ashlandcountywi.gov', '715-413-1928'),
            "16": ('Shawn Sederholm', 'shawn.sederholm@ashlandcountywi.gov', '715-209-0841'),
            "17": ('Terrance Van Buren', 'terrance.vanburen@ashlandcountywi.gov', None),
            "18": ('James R. Schultz', 'james.schultz@ashlandcountywi.gov', '715-278-3781'),
            "19": ('Gary Eder. Jr.', 'gary.eder@ashlandcountywi.gov', '715-663-0727'),
            "20": ('(Wilfred) David Meindl', 'dave.meindl@ashlandcountywi.gov', '715-769-3355'),
            "21": ('Gary A. Mertig', 'gary.mertig@ashlandcountywi.gov', '715-661-0243'),
        },
    },
    {
        "fips": "55033", "name": "Dunn", "seats": 29,
        "read_on": "2026-08-31",
        "source_url": "https://dunncountywi.gov/supervisors",
        "how": "read from the county's own page before its robots.txt was "
               "checked; that file disallows the whole site to every agent it "
               "does not name, so this roster is never re-fetched",
        "why": "The county asks automated readers not to crawl its site, so "
               "this name is a dated capture rather than the weekly re-read "
               "the other named counties get.",
        "roles": {"5": "Vice Chair", "24": "Chair"},
        # district -> (name, e-mail, phone); the page publishes neither
        "members": {
            "1": ("Tim Lauffer", None, None),
            "2": ("John Wurtzler", None, None),
            "3": ("Albert Kelly", None, None),
            "4": ("Ronald P. Score", None, None),
            "5": ("Gary Stene", None, None),
            "6": ("Dustin Shackleton", None, None),
            "7": ("Gary Bjork", None, None),
            "8": ("Luke Wilsey", None, None),
            "9": ("Samuel Thompson", None, None),
            "10": ("Donald Gjestson", None, None),
            "11": ("Michelle Bachand", None, None),
            "12": ("Mike Kneer", None, None),
            "13": ("Monica Berrier", None, None),
            "14": ("Agnes Welsch", None, None),
            "15": ("Barbara Lyon", None, None),
            "16": ("Tom Wagner", None, None),
            "17": ("Kelly McCullough", None, None),
            "18": ("Sheila Stori", None, None),
            "19": ("Cody Gentz", None, None),
            "20": ("Spencer Berndt", None, None),
            "21": ("Diane L. Morehouse", None, None),
            "22": ("Andrew Hagen", None, None),
            "23": ("Mark Thomas", None, None),
            "24": ("Randy L. Prochnow", None, None),
            "25": ("Tom Gilbert", None, None),
            "26": ("Larry R. Bjork", None, None),
            "27": ("Robert Bauer", None, None),
            "28": ("Tim Lienau", None, None),
            "29": ("David Styer", None, None),
        },
    },
    {
        "fips": "55053", "name": "Jackson", "seats": 19,
        "read_on": "2026-08-31",
        "source_url": "https://www.co.jackson.wi.us/index.asp?SEC=219B0002-A26C-4AA7-B330-980B6D3ADB57",
        "document_url":
            "https://www.co.jackson.wi.us/vertical/sites/%7B4C09F8F2-A8A2-4929-9E2A-A836851B00CC%7D/uploads/2026_-_2027_County_Board_Members.pdf",
        "how": "read from the county's own page before its robots.txt was "
               "checked; that file disallows the whole site to every agent it "
               "does not name, so this roster is never re-fetched",
        "why": "The county asks automated readers not to crawl its site, so "
               "this name is a dated capture rather than the weekly re-read "
               "the other named counties get.",
        # district -> (name, e-mail, phone); None is a seat the county marks empty
        "members": {
            "1": ("Brian Bethke", "Brian.Bethke@jacksoncountywi.gov", "715-533-9941"),
            "2": ("David Holen", "David.Holen@jacksoncountywi.gov", "715-896-1003"),
            "3": ("Hoyt Strandberg", "Hoyt.Strandberg@jacksoncountywi.gov", "715-299-1586"),
            "4": ("Daryl Boe", "Daryl.Boe@jacksoncountywi.gov", "715-896-1071"),
            "5": ("Michael Beck", "Michael.Beck@jacksoncountywi.gov", "608-343-1742"),
            "6": ("Mike Kunes", "Mike.Kunes@jacksoncountywi.gov", "715-299-4561"),
            "7": ("Russell Anderson", "Russell.Anderson@jacksoncountywi.gov", "715-963-2133"),
            "8": ("Max Hart", "Max.Hart@jacksoncountywi.gov", "715-896-4508"),
            "9": ("Bill Laurent", "Bill.Laurent@jacksoncountywi.gov", "715-641-4519"),
            "10": ("Nicole Pettibone", "Nicole.Pettibone@jacksoncountywi.gov", "715-299-2849"),
            "11": ("Garth Rolbiecki", "Garth.Rolbiecki@jacksoncountywi.gov", "715-773-2954"),
            "12": ("Ron Carney", "Ron.Carney@jacksoncountywi.gov", "608-387-9604"),
            "13": ("Dale Hoff", "Dale.Hoff@jacksoncountywi.gov", "715-284-2720"),
            "14": ("John Higgins", "John.Higgins@jacksoncountywi.gov", "715-299-2132"),
            "15": ("Sarah Peloquin", "Sarah.Peloquin@jacksoncountywi.gov", "608-792-3391"),
            "16": ("Desiree Gearing-Lancaster", "Desiree.Gearing-Lancaster@jacksoncountywi.gov", "715-284-2815"),
            "17": ("Reed Richardson", "Reed.Richardson@jacksoncountywi.gov", "715-577-7226"),
            "18": ("Jerry Schmidt", "Jerrold.Schmidt@jacksoncountywi.gov", "715-896-5478"),
            "19": ("Ed Chamberlain", "Edward.Chamberlain@jacksoncountywi.gov", "715-896-0016"),
        },
    },
    {
        "fips": "55103", "name": "Richland", "seats": 21,
        "read_on": "2026-08-31",
        "source_url": "https://richlandcountywi.gov/index.asp?SEC=DB387A4E-E124-4584-B32C-2C95880C63F0",
        "how": "read from the county's own page before its robots.txt was "
               "checked; that file disallows the whole site to every agent it "
               "does not name, so this roster is never re-fetched",
        "why": "The county asks automated readers not to crawl its site, so "
               "this name is a dated capture rather than the weekly re-read "
               "the other named counties get.",
        # district -> (name, e-mail, phone); None is a seat the county marks empty
        "members": {
            "1": ("Steve Carrow", None, None),
            "2": ("Mary Miller", None, None),
            "3": ("Randy E. Schoonover", None, None),
            "4": ("Sandra M. Kramer", None, None),
            "5": ("Richard D McKee", None, None),
            "6": ("Larry Engel", None, None),
            "7": ("Steve Meyer", None, None),
            "8": ("Shirley Welte", None, None),
            "9": ("Tiffany Thompson", None, None),
            "10": ("Kevin Nolen", None, None),
            "11": ("Rod C. Perry", None, None),
            "12": ("Mary Collins-Johnsrud", None, None),
            "13": ("David Turk", None, None),
            "14": ("Darlene Waldsmith-Tagliapietra", None, None),
            "15": ("Melvin (Bob) Frank", None, None),
            "16": ("Kerry Severson", None, None),
            "17": ("Steve Williamson", None, None),
            "18": ("Marc Couey", None, None),
            "19": ("Randy Schmidt", None, None),
            "20": ("Duane McElvain", None, None),
            "21": ("Daniel J. McGuire", None, None),
        },
    },
    {
        "fips": "55107", "name": "Rusk", "seats": 19,
        "read_on": "2026-08-31",
        "source_url": "https://ruskcounty.org/supervisors",
        "how": "read from the county's own page before its robots.txt was "
               "checked; that file disallows the whole site to every agent it "
               "does not name, so this roster is never re-fetched",
        "why": "The county asks automated readers not to crawl its site, so "
               "this name is a dated capture rather than the weekly re-read "
               "the other named counties get.",
        "roles": {"12": "Vice-Chairman", "19": "Chairman"},
        # district -> (name, e-mail, phone); None is a seat the county marks empty
        "members": {
            "1": ("Alec Hampton", None, None),
            "2": ("Jerry Biller", None, None),
            "3": None,
            "4": ("John Moore", None, None),
            "5": ("Terry Wedwick", None, None),
            "6": None,
            "7": ("Bill Stewart", None, None),
            "8": ("Tom Cudo", None, None),
            "9": ("Lisa Podgornik", None, None),
            "10": ("Anton Ziesler", None, None),
            "11": ("Phil Schneider", None, None),
            "12": ("Jim Meyer", None, None),
            "13": ("Kurt Gorsegner", None, None),
            "14": ("Jeremy Vincent", None, None),
            "15": ("Tom Hanson", None, None),
            "16": ("Lois Goode", None, None),
            "17": ("Dave Willingham", None, None),
            "18": ("Mike Russell", None, None),
            "19": ("Ron Freeman", None, None),
        },
    },
    {
        "fips": "55095", "name": "Polk", "seats": 15,
        "read_on": "2026-08-31",
        "source_url": "https://www.polkcountywi.gov/government/county_board_of_supervisors/index.php",
        "how": "read from the county's own page before its robots.txt was "
               "checked; that file disallows the whole site to every agent it "
               "does not name, so this roster is never re-fetched",
        "why": "The county asks automated readers not to crawl its site, so "
               "this name is a dated capture rather than the weekly re-read "
               "the other named counties get.",
        "roles": {"11": "2nd Vice Chair", "13": "Chair", "15": "1st Vice Chair"},
        # district -> (name, e-mail, phone); None is a seat the county marks empty
        "members": {
            "1": ("Brad Olson", None, None),
            "2": ("Doug Route", None, None),
            "3": ("Jim Bethke", None, None),
            "4": ("Pam Garvey", None, None),
            "5": ("Scott Gilbertson", None, None),
            "6": ("Adam Jarchow", None, None),
            "7": ("Sharon Kelly", None, None),
            "8": ("Jeremy Hall", None, None),
            "9": ("Kim O'Connell", None, None),
            "10": ("Alice Moris", None, None),
            "11": ("Jay Luke", None, None),
            "12": ("Fran Duncanson", None, None),
            "13": ("Russ Arcand", None, None),
            "14": ("Keith Karpenski", None, None),
            "15": ("John Bonneprise", None, None),
        },
    },
    # PEPIN (2026-08-31) — THE FIRST ENTRY HERE HELD BACK BY A ROBOTS.TXT RATHER
    # THAN BY A CHALLENGE, and the distinction is the whole reason it is carried.
    # Taylor answers a captcha and Lafayette a Cloudflare interstitial: those are
    # doors that will not open for this client. co.pepin.wi.us opens perfectly
    # well and ASKS not to be crawled:
    #
    #     User-agent: Googlebot        Disallow: /admin/ /manager/ ...
    #     User-agent: bingbot          (the same)
    #     User-agent: ia_archiver      /admin/ /manager/
    #     User-agent: archive.org_bot  /admin/ /manager/
    #     User-agent: W3C-checklink    /admin/ /manager/
    #     User-agent: CCBot            /admin/ /manager/
    #     User-agent: *                Disallow: /
    #
    # This scraper is none of the named agents, so it falls to the `*` group and
    # the whole site is disallowed to it. THAT IS THE EXACT OPPOSITE OF IOWA AND
    # WAUSHARA, the two counties whose robots.txt this file already records: the
    # note in COUNTIES turns on the fact that "in BOTH files the `User-agent: *`
    # group permits the board path", which is what made reading them the
    # operator's call to make. Here it permits nothing, so there is no weekly
    # fetch and deliberately NO `live` key — an entry with one would re-request
    # the page every run, which is the single thing the county has asked not to
    # happen.
    #
    # A ROBOTS.TXT GOVERNS CRAWLERS, NOT READERS. The operator opened
    # co.pepin.wi.us/bos in an ordinary browser and transcribed it, which is the
    # route the file leaves open, exactly as a person passing Taylor's captcha
    # is. The roster below is that transcription.
    #
    # IT WAS CROSS-CHECKED AGAINST THE ONE FETCH THIS FILE MADE BEFORE READING
    # THE POLICY, and the two agree on all twelve names, all twelve phones and
    # all ten mailboxes — recorded here because that fetch happened and saying
    # so is cheaper than pretending it did not.
    #
    # WHAT THIS ENTRY DOES NOT CLAIM: that nothing in this repo touches the
    # host. scripts/validate_card_links.py probes every shipped URL monthly and
    # already probed four on co.pepin.wi.us before this entry existed (the
    # county's directory link and three officer-contact pages in
    # wi_county_officer_contact_scraper.py, which runs WEEKLY in two workflows);
    # this adds a fifth. What is avoided here is the weekly roster crawl. The
    # rest is a wider question than one county — six other hosts this repo
    # fetches weekly publish the same `*  Disallow: /` — and is recorded rather
    # than quietly half-fixed.
    #
    # THE MAILBOXES USE THREE PREFIXES, WHICH IS WHY NONE IS DERIVED. Ten of the
    # twelve publish a district-keyed address and they are NOT one pattern:
    # pcsdist1@, pcdistrict2@, pcsdist3@, pcsdist6@, pcdist7@, pcsdist8@,
    # pcsdist9@, pcsdist10@, pcdistrict11@, pcsdist12@. A `pcsdist<n>@` rule
    # would invent wrong addresses for districts 2, 7 and 11, so every one is
    # transcribed. Districts 4 and 5 publish none and carry none.
    #
    # THE HOME ADDRESSES ARE NOT CARRIED — the page prints one per supervisor,
    # and the fleet's standing rule is that a home address never ships. The
    # county clerk (Audrey Bauer, Secretary to the Board) is on the same page and
    # is NOT a supervisor; she is not in this table.
    {
        "fips": "55091", "name": "Pepin", "seats": 12,
        "read_on": "2026-08-31",
        "source_url": "https://www.co.pepin.wi.us/bos",
        "how": "transcribed from the county's own Board of Supervisors page by "
               "the operator in a browser; the site's robots.txt disallows the "
               "whole site to every agent it does not name, so this roster is "
               "never re-fetched",
        # THE READER-FACING HALF OF `how`, because the card's own sentence is
        # wrong for this county. It says a carried roster is dated "because the
        # county's website refuses automated readers", which is true of Taylor's
        # captcha and Lafayette's challenge and NOT true here: Pepin's site
        # serves this client perfectly well and its robots.txt asks automated
        # clients not to read it. Telling a reader the county refuses them would
        # misdescribe what the county actually did.
        "why": "The county asks automated readers not to crawl its site, so "
               "this name is a dated capture rather than the weekly re-read the "
               "other named counties get.",
        "roles": {"8": "Chairperson", "9": "Vice-Chairperson",
                  "12": "2nd Vice-Chairperson"},
        # district -> (name, e-mail, phone)
        "members": {
            "1": ("Michael Wright", "pcsdist1@co.pepin.wi.us", "715-926-3210"),
            "2": ("Gary S. Bauer", "pcdistrict2@co.pepin.wi.us", "715-495-1532"),
            "3": ("Andy Winkler", "pcsdist3@co.pepin.wi.us", "715-577-9534"),
            "4": ("Joe Schieffer", None, "715-495-7217"),
            "5": ("Randall Weiss", None, "715-495-7429"),
            "6": ("Elizabeth Bauer", "pcsdist6@co.pepin.wi.us", "504-723-3560"),
            "7": ("Kris Sabelko", "pcdist7@co.pepin.wi.us", "715-505-3936"),
            "8": ("Tom Milliren", "pcsdist8@co.pepin.wi.us", "715-495-6597"),
            "9": ("John C. Andrews", "pcsdist9@co.pepin.wi.us", "715-279-3058"),
            "10": ("Kevin C. Kosok", "pcsdist10@co.pepin.wi.us", "715-495-1761"),
            "11": ("Vicki Kosok", "pcdistrict11@co.pepin.wi.us", "715-442-3071"),
            "12": ("Angie Bocksell", "pcsdist12@co.pepin.wi.us", "715-559-0830"),
        },
    },
    {
        "fips": "55119", "name": "Taylor", "seats": 17,
        "read_on": "2026-08-29",
        "source_url": "https://co.taylor.wi.us/directory/county-board/",
        "how": "read from the county's own directory page in a browser by the "
               "operator; the host answers a captcha to every automated client",
        # district -> (name, e-mail, phone)
        "members": {
            "1": ("Lisa Carbaugh", "lisa.carbaugh@co.taylor.wi.us", "715-965-1980"),
            "2": ("Tim Hansen", "tim.hansen@co.taylor.wi.us", "715-965-7662"),
            "3": ("Susan Swiantek", "sue.swiantek@co.taylor.wi.us", "715-560-9409"),
            "4": ("Michael Bub", "michael.bub@co.taylor.wi.us", "715-965-7748"),
            "5": ("Loren (Jim) Metz", "jim.metz@co.taylor.wi.us", "715-748-0740"),
            "6": ("Scott Mildbrand", "scott.mildbrand@co.taylor.wi.us", "715-748-3988"),
            "7": ("Lorie Floyd", "lorie.floyd@co.taylor.wi.us", "608-412-2974"),
            "8": ("Charles Zenner", "chuck.zenner@co.taylor.wi.us", "715-678-2172"),
            "9": ("Diane J. Albrecht", "diane.albrecht@co.taylor.wi.us", "715-748-5471"),
            "10": ("Catherine Lemke", "catherine.lemke@co.taylor.wi.us", "715-748-5694"),
            "11": ("James Gebauer", "jim.gebauer@co.taylor.wi.us", "715-748-4871"),
            "12": ("Rollie Thums", "rollie.thums@co.taylor.wi.us", "715-427-5809"),
            "13": ("Harvey 'Bud' Suckow", "bud.suckow@co.taylor.wi.us", "715-897-4514"),
            "14": ("Karen Cummings", "karen.cummings@co.taylor.wi.us", "715-668-5226"),
            "15": ("Lynette Rosemeyer", "lynn.rosemeyer@co.taylor.wi.us", "715-827-0027"),
            "16": ("Darrell Thompson", "darrell.thompson@co.taylor.wi.us", "715-644-8285"),
            "17": ("Rodney Adams", "rod.adams@co.taylor.wi.us", "715-678-2397"),
        },
    },
    # LAFAYETTE (2026-08-29), AND THE ONE ENTRY HERE THAT IS RE-TRIED LIVE.
    # lafayettecountywi.org and its www host both answer HTTP 403 carrying
    # Cloudflare's own "Just a moment..." interstitial (cf-mitigated:
    # challenge, server: cloudflare, a cf-ray) to a client sending full
    # browser headers. A managed challenge is an access control and is not
    # defeated here. But unlike Taylor — whose other three hosts do not
    # resolve at all — this county has a PAGE that parses: /bos lists all
    # sixteen seats as "Larry Ludlum- Supervisor District #1", which
    # `same-line-lead` reads 16/16 against the Internet Archive's own
    # 2025-02-14 capture of it. So `live` is pinned here and tried on every
    # run: the day the challenge lifts, the run says so and this entry can be
    # deleted in favour of a COUNTIES row.
    #
    # WITNESSES. The Archive's capture agrees name for name on districts 1-15
    # and disagrees on 16 (it has Rita R. Buchholz; the county now has David
    # Halloran) — a real turnover, and exactly why an eighteen-month-old
    # capture is a witness for the fifteen and never a source for the
    # sixteenth. The chair is the Blue Book's chair for this county, and the
    # clerk the page names (Carla M Jacobson) is the clerk wi-county-clerks
    # already carries for 55065.
    #
    # NO E-MAILS OR PHONES: the page publishes none per supervisor, so those
    # slots are empty rather than filled from anywhere else.
    {
        "fips": "55065", "name": "Lafayette", "seats": 16,
        "read_on": "2026-08-29",
        "source_url": "https://www.lafayettecountywi.org/bos",
        "how": "captured from the county's own Board of Supervisors page, which "
               "answers a Cloudflare managed challenge to every automated client",
        "live": {"strategy": "same-line-lead"},
        # District 3's own row says "County Board Chairman"; the two vice-chairs
        # come from the administration block above the list. Both are what
        # `same-line-lead` and `attach_named_officer_roles` recover when the
        # page is read live, so the document and the live read agree.
        "roles": {"3": "Chairman", "12": "2nd Vice Chair", "15": "1st Vice Chair"},
        "members": {
            "1": ("Larry Ludlum", None, None),
            "2": ("Mark Pinch", None, None),
            "3": ("Jack Sauer", None, None),
            "4": ("John E. Reichling", None, None),
            "5": ("Luke McGuire", None, None),
            "6": ("Jeff Berget", None, None),
            "7": ("Bob Boyle", None, None),
            "8": ("Jed Gant", None, None),
            "9": ("Joe Schutte", None, None),
            "10": ("Gary Benson", None, None),
            "11": ("Donna Flannery", None, None),
            "12": ("Carmen McDonald", None, None),
            "13": ("Lee A. Gill", None, None),
            "14": ("Emmett Reilly", None, None),
            "15": ("Scott Pedley", None, None),
            "16": ("David Halloran", None, None),
        },
    },
    {
        "fips": "55063", "name": "La Crosse", "seats": 30,
        "read_on": "2026-08-29",
        "source_url": "https://lacrossecounty.org/countyboard/members",
        "how": "read from the county's own members page in a browser by the "
               "operator; Cloudflare answers 403 to every automated client "
               "on every path of the host",
        # The BOARD offices only. Two more supervisors carry a title on the
        # same page and both are standing-committee chairs, not board
        # officers — see the docstring; shipping them would give the board
        # three chairs, which document_county refuses outright.
        "roles": {"3": "1st Vice Chair", "10": "2nd Vice Chair", "13": "Chair"},
        # district -> (name, e-mail, phone). The page publishes no e-mail
        # address in its text (a bare "Email" link per member), so every
        # e-mail here is empty and none ships. Phones are the county's own,
        # verbatim, spacing and all.
        "members": {
            "1": ("Kelly Leibold", "", "507 272 5408"),
            "2": ("Ralph Geary", "", "608-519-6175"),
            "3": ("David Pierce", "", "608-343-1031"),
            "4": ("Kathy Allen", "", ""),
            "5": ('Emily "Em" Anderson', "", "262-744-4982"),
            "6": ("Grant Mathu", "", "(608) 518-0368"),
            "7": ("Beth Piggush", "", "860-371-0130"),
            "8": ("Peggy Isola", "", "608-519-7365"),
            "9": ("Angie Manke", "", ""),
            "10": ("Kim Cable", "", ""),
            "11": ("Patrick Scheller", "", "608-769-8502"),
            "12": ("Randy Erickson", "", "608-519-6292"),
            "13": ("Tina Tryggestad", "", "608-790-2912"),
            "14": ("Steve Duffrin", "", "608-780-2247"),
            "15": ("Monica Kruse", "", "608-738-9195"),
            "16": ("Dan Ferries", "", "608-780-7282"),
            "17": ("Lia Manock", "", "608-315-2855"),
            "18": ("Joanna Drazkowski", "", "612-387-8820"),
            "19": ("Anna McBride", "", "608-385-6701"),
            "20": ("Steve Doyle", "", "608-783-1204"),
            "21": ("Jeff Fimreite", "", "608-780-9966"),
            "22": ("Joe Kovacevich", "", "608-215-0664"),
            "23": ("Joseph (Joe) Carty", "", "608-799-3701"),
            "24": ("Kristie Tweed", "", "608-317-1331"),
            "25": ('Dennis "Jake" Jacobsen', "", "1-715-572-7948"),
            "26": ("Beth Arentz-Clements", "", ""),
            "27": ("Paul Wuensch", "", "608-386-7830"),
            "28": ("Ron Rothering", "", "608-780-3086"),
            "29": ("Ken Schlimgen", "", "608-786-4382"),
            "30": ("Dillon Mader", "", "608-792-6650"),
        },
    },
]


def marks_chair(role):
    """The board-officer test, identical to build_wi_county_officer_roster.py's:
    "Chair"/"Chairwoman" mark the chair, "1st/2nd Vice Chair" never do."""
    f = " ".join(str(role or "").lower().split())
    return "chair" in f and "vice" not in f


assert marks_chair("Chair") and not marks_chair("1st Vice Chair")


def document_county(spec):
    """A roster carried from a document, with its age stated on every run.

    Returns (districts, carried_from_document).

    THE LIVE PAGE IS TRIED FIRST WHERE THERE IS ONE TO TRY (`live`), and that
    is the difference between an entry that can leave this table and one that
    cannot. Taylor has no host that answers anything, so its rows are a
    document until somebody re-reads the page in a browser. Lafayette has a
    page that parses under a pinned reading and a host that refuses this
    client — twice now this project has recorded a block that described its
    own vantage rather than the world (city.milwaukee.gov answered GitHub's
    runners plain, and the Elections Commission simply sent the file), so the
    attempt is made on every run and the log says which way it went.
    """
    import datetime
    live = spec.get("live")
    if live:
        try:
            # SCRAPE_COUNTY RETURNS (districts, read_from) — and this line took
            # the whole tuple until 2026-09-02, when Lafayette's page answered
            # for the first time and the run died three counties later on
            # `districts.values()`. A retry path guarded by "this will probably
            # keep failing" is exercised only on the day it stops failing, which
            # is the day it must not be the thing that breaks: the weekly job
            # would have gone red on the good news that a county came back.
            districts = scrape_county(spec["fips"], spec["name"], spec["seats"],
                                      live["strategy"], spec["source_url"])[0]
            print("  ok   %-12s %d seats READ LIVE \u2014 the page answered this run, "
                  "so this DOCUMENT_ROSTERS entry can be retired and the county "
                  "moved to COUNTIES with the %r reading"
                  % (spec["name"], spec["seats"], live["strategy"]), file=sys.stderr)
            return districts, False
        except Exception as e:      # noqa: BLE001 - refusal is the expected case
            print("  live %-12s still refused (%s)" % (spec["name"], e),
                  file=sys.stderr)
    read = datetime.date(*map(int, spec["read_on"].split("-")))
    age = (datetime.date.today() - read).days
    print("  NOT RE-READ %-12s %d seats from a document read %s (%d days ago)"
          % (spec["name"], spec["seats"], spec["read_on"], age), file=sys.stderr)
    members = spec["members"]
    want = {str(d) for d in range(1, spec["seats"] + 1)}
    if set(members) != want:
        missing = sorted(int(k) for k in want - set(members))
        raise RuntimeError("%s: the document carries %d of %d districts (missing %s)"
                           % (spec["name"], len(members), spec["seats"], missing))
    names = [v[0] for v in members.values() if v is not None]
    if len(set(names)) != len(names):
        dupes = sorted({n for n in names if names.count(n) > 1})
        raise RuntimeError("%s: the same person is filed under two districts (%s)"
                           % (spec["name"], dupes))
    # Board offices are declared apart from the transcription, so a title the
    # county prints beside a name never becomes a role by merely being there.
    roles = spec.get("roles", {})
    stray = sorted(set(roles) - set(members), key=lambda d: int(d) if d.isdigit() else 0)
    if stray:
        raise RuntimeError("%s: a role is filed under district(s) %s, which the "
                           "board does not have" % (spec["name"], stray))
    empty = sorted(d for d in roles if members.get(d) is None)
    if empty:
        raise RuntimeError("%s: a role is filed under district(s) %s, which the "
                           "county marks vacant" % (spec["name"], empty))
    chairs = sorted(d for d, r in roles.items() if marks_chair(r))
    if len(chairs) > 1:
        # La Crosse prints "Chair, <standing committee>" in the same slot as
        # its board chair's title; a board has one chair, so two here means a
        # committee chair was read as an officer.
        raise RuntimeError("%s: %d districts are marked chair (%s) — a board has one"
                           % (spec["name"], len(chairs), chairs))
    out = {}
    for d in range(1, spec["seats"] + 1):
        seat = members[str(d)]
        # A SEAT THE COUNTY ITSELF MARKS EMPTY IS `None`, not a row of blanks.
        # Rusk carries two, and before this the carried path could only ever
        # say "vacant": False — so a county with a vacancy could not be carried
        # at all without asserting somebody holds the seat.
        if seat is None:
            out[str(d)] = {"name": None, "vacant": True, "role": None}
            continue
        name, email, phone = seat
        row = {"name": name, "vacant": False, "role": roles.get(str(d))}
        if email:
            row["email"] = email
        if phone:
            row["phone"] = phone
        out[str(d)] = row
    return out, True


# =============================================================================
# COUNTIES WHOSE ROSTER RIDES THE INTERNET ARCHIVE (added 2026-08-29)
# =============================================================================
# THE THIRD CARRIER, after a page this client can fetch and a county's own GIS
# layer. Fond du Lac publishes a County Board Supervisors directory that is
# richer than most of the counties that already ship — a name, a district, a
# county e-mail and a phone for all twenty-five seats, with the Chair and both
# Vice Chairs titled — and this client cannot read a byte of it: every path on
# www.fdlco.wi.gov answers HTTP 403 from AkamaiGHost with the CDN's own "Access
# Denied" body, to every user-agent tried, over http and https alike. That is a
# client-fingerprint block on a datacenter address, not a refusal to publish,
# and the proof is that the Internet Archive's own crawler has been fetching
# the page successfully for years.
#
# So the county's own page is read through a public archive OF THAT PAGE. Not
# evasion — nothing here defeats the block, and a captcha would end the matter
# (see Taylor) — a second reader of a document the county publishes to the
# world, with the copy's timestamp carried into the run log for provenance.
# The Illinois side reached the same arrangement for Kendall and McHenry first
# (scripts/kendall_county_board_scraper.py's WaybackFetcher); this is that
# posture with Wisconsin's own gates around it.
#
# FRESHNESS IS THE WHOLE PROBLEM, AND IT IS MEASURED RATHER THAN ASSUMED.
# A snapshot is a photograph, and an old one shows a board that has since
# changed while looking exactly like a current one. Two measurements set the
# rules below, both taken 2026-08-29 from the Archive's own CDX index:
#
#   1. NATURAL CRAWLING IS NOT ENOUGH. The captures of page 1 over the past
#      year run 2025-08-15, 2025-10-02, ... 2026-02-09, 2026-05-05, 2026-05-11
#      and then nothing — gaps of 48, 85 and (at the time of writing) 110 days.
#      A roster resting on whatever the crawler happened to take would be
#      months stale for months at a time and never say so. SAVE PAGE NOW is
#      therefore the primary route: each run asks the Archive to take a FRESH
#      capture of each page, and only falls back to the newest existing one.
#   2. THE TWO PAGES CAN BE FROM DIFFERENT WORLDS. The directory paginates at
#      twenty, so twenty-five supervisors need two fetches — and on the day
#      this was written the newest capture of page 1 was 2026-05-11 while the
#      newest of page 2 was 2026-03-16. Wisconsin's county boards are ALL
#      reseated at the April spring election, so those two captures sit on
#      opposite sides of one, and stitching them would have shipped five
#      supervisors (districts 2, 4, 7, 16 and 21) who might no longer hold
#      their seats, presented beside twenty who certainly did. Nothing about
#      the merged result would have looked wrong. Hence PAGE_SPREAD_DAYS: the
#      pages must be captured close to each other as well as recently.
#
# Both limits FAIL LOUDLY rather than degrading. A county that cannot be read
# freshly is skipped for the run and its card goes back to linking the board,
# which is the same thing that happens to any county whose page reshapes.
WAYBACK_MAX_AGE_DAYS = 45     # Kendall's number, and for Kendall's reason
PAGE_SPREAD_DAYS = 14         # see measurement 2 above — an April election is
                              # the thing this stops a merge from straddling
WAYBACK_AVAILABLE = "https://archive.org/wayback/available?url=%s"
WAYBACK_SAVE = "https://web.archive.org/save/%s"
WAYBACK_RAW = "https://web.archive.org/web/%sid_/%s"

ARCHIVE_COUNTIES = [
    {
        "fips": "55039", "name": "Fond Du Lac", "seats": 25,
        # Page 1 is the source_url a reader is sent to; page 2 exists only
        # because the county's directory widget paginates at twenty. The pager
        # states its own arithmetic ("1 - 20 of 25 items"), which is what the
        # gates below check rather than trusting this list to stay complete.
        "pages": [
            "https://www.fdlco.wi.gov/government/county-board-supervisors",
            "https://www.fdlco.wi.gov/government/county-board-supervisors/-npage-2",
        ],
        "source_url": "https://www.fdlco.wi.gov/government/county-board-supervisors",
        "email_domain": "@fdlco.wi.gov",
        "min_emails": 23,     # 25 today; a page that stops publishing them fails
        "min_phones": 23,
    },
]


def _spn_save(url):
    """Ask Save Page Now for a fresh capture; return its 14-digit timestamp.

    Anonymous by default. ARCHIVE_SPN_ACCESS_KEY / ARCHIVE_SPN_SECRET_KEY (the
    same repo secrets Illinois' Kendall and McHenry workflows already pass)
    switch on the SPN2 job API, which is the reliable path when a shared runner
    address has spent the anonymous quota. Absent keys are not an error.
    """
    key = os.environ.get("ARCHIVE_SPN_ACCESS_KEY")
    secret = os.environ.get("ARCHIVE_SPN_SECRET_KEY")
    if key and secret:
        try:
            data = urllib.parse.urlencode({"url": url}).encode()
            req = urllib.request.Request(
                "https://web.archive.org/save", data=data,
                headers=dict(ARCHIVE_UA, Accept="application/json",
                             Authorization="LOW %s:%s" % (key, secret)))
            with urllib.request.urlopen(req, timeout=60) as r:
                job = json.load(r).get("job_id")
            if job:
                for _ in range(30):          # ~2.5 minutes, SPN2's own pace
                    time.sleep(5)
                    req = urllib.request.Request(
                        "https://web.archive.org/save/status/" + job,
                        headers=dict(ARCHIVE_UA, Accept="application/json",
                                     Authorization="LOW %s:%s" % (key, secret)))
                    with urllib.request.urlopen(req, timeout=30) as r:
                        st = json.load(r)
                    if st.get("status") == "success":
                        return st.get("timestamp")
                    if st.get("status") == "error":
                        break
        except Exception as e:              # noqa: BLE001 - save is best-effort
            print("    SPN2 save failed (%s): %s" % (url, e), file=sys.stderr)
    try:
        req = urllib.request.Request(WAYBACK_SAVE % url, headers=ARCHIVE_UA)
        with urllib.request.urlopen(req, timeout=180) as r:
            m = re.search(r"/web/(\d{14})", r.geturl() or "")
            if not m:
                m = re.search(r"/web/(\d{14})", r.headers.get("Content-Location", "") or "")
            if m:
                return m.group(1)
    except Exception as e:                  # noqa: BLE001 - save is best-effort
        print("    Save Page Now unavailable (%s): %s" % (url, e), file=sys.stderr)
    return None


def _wayback_latest(url):
    """Timestamp of the newest existing snapshot, or None."""
    try:
        req = urllib.request.Request(
            WAYBACK_AVAILABLE % urllib.parse.quote(url, safe=""),
            headers=ARCHIVE_UA)
        with urllib.request.urlopen(req, timeout=60) as r:
            snap = (json.load(r).get("archived_snapshots") or {}).get("closest") or {}
        return snap.get("timestamp") or None
    except Exception:                       # noqa: BLE001 - reachability probe
        return None


BLOCK_PAGE = re.compile(r"(?i)<title>\s*(?:Access Denied|Just a moment)")


def _snapshot_age_days(ts):
    import datetime
    taken = datetime.datetime.strptime(ts, "%Y%m%d%H%M%S").replace(
        tzinfo=datetime.timezone.utc)
    return (datetime.datetime.now(datetime.timezone.utc) - taken).days


def _cdx_latest(url):
    """The newest 200 capture CDX lists, or None. The availability API and CDX
    do not always agree about what the Archive holds, so both are asked."""
    try:
        rows = _archive_json(CDX % urllib.parse.quote(url, safe=""))
    except Exception:                       # noqa: BLE001 - reachability probe
        return None
    stamps = sorted(r[0] for r in rows[1:]) if rows and rows[0][0] == "timestamp" \
        else sorted(r[0] for r in rows)
    return stamps[-1] if stamps else None


def fetch_archived(url):
    """(html, timestamp) for the county's page, read through the Archive.

    A fresh capture is REQUESTED first and the newest existing one is only the
    fallback; either way the copy's age is checked before it is parsed, so a
    stale archive fails the county loudly instead of shipping old officeholders
    behind a current-looking card.
    """
    ts = _spn_save(url) or _wayback_latest(url) or _cdx_latest(url)
    if ts is None:
        raise RuntimeError("no archive snapshot available for %s" % url)
    # WIS. STAT. 59.10(3)(d): supervisors take office at the third-Tuesday-in-
    # April organizational meeting, so a capture older than the sitting board's
    # own seating names a board that no longer sits — a different question from
    # the age ceiling below, and the one that actually protects the names.
    seated = board_seated_on().strftime("%Y%m%d")
    if ts[:8] < seated:
        raise RuntimeError(
            "the newest archived capture of %s is %s, older than the %s "
            "organizational meeting that seated this board (Wis. Stat. "
            "59.10(3)(d)) — it names a board that no longer sits"
            % (url, ts[:8], seated))
    age = _snapshot_age_days(ts)
    if age > WAYBACK_MAX_AGE_DAYS:
        raise RuntimeError(
            "the newest archive copy of %s is %d days old (limit %d) and Save Page "
            "Now did not take a fresh one — refusing to ship officeholders read "
            "from it" % (url, age, WAYBACK_MAX_AGE_DAYS))
    # verified TLS only: see fetch_bytes
    page = fetch(WAYBACK_RAW % (ts, url), ARCHIVE_UA, allow_lax_tls=False)
    if BLOCK_PAGE.search(page):
        raise RuntimeError("the archived copy of %s is itself a block page (%s)"
                           % (url, ts))
    return page, ts


def fetch_page(url):
    """(html, archived_at_or_None) — the county's own server first, the Archive
    second. The direct rung costs one request and is tried on every run rather
    than being written off: this project has twice recorded a county as blocked
    on the strength of one client's view (Knox's website, Gallatin's TLS chain),
    and a block that lifts should be noticed by the scraper, not by a person."""
    try:
        page = fetch(url, timeout=30)
        if not BLOCK_PAGE.search(page):
            return page, None
    except Exception:                       # noqa: BLE001 - the expected path
        pass
    return fetch_archived(url)


# --- reading a Granicus business-directory page -------------------------------
# The generic readers above flatten a page to lines and hunt for a district
# beside a name. This county's directory is STRUCTURED — one <h2 class=
# "detail-title"> per supervisor followed by a labelled <ul class="detail-list">
# — so it is read as the markup it is, which is what makes the e-mail and phone
# reachable at all. Deliberately a separate reader rather than a sixth reading
# direction: the thirty counties on the line readers keep byte-identical
# behaviour, the same reason `_windowed_strict` did not become a flag on
# `_windowed`.
_ENTRY = re.compile(r'(?is)<h2[^>]*class="[^"]*detail-title[^"]*"[^>]*>(.*?)</h2>\s*'
                    r'(?:<ul[^>]*class="[^"]*detail-list[^"]*"[^>]*>(.*?)</ul>)?')
_FIELD = re.compile(r'(?is)<span[^>]*detail-list-label[^>]*>(.*?)</span>\s*'
                    r'<span[^>]*detail-list-value[^>]*>(.*?)</span>')
_PAGER = re.compile(r"(\d+)\s*[-–]\s*(\d+)\s+of\s+(\d+)\s+items")
# A SUFFIX IS NEVER ONE LETTER, and that rule cost a name. The county writes
# "Sippel, James V." — a middle initial — and a suffix pattern that accepted a
# lone roman "V" flipped it to "James Sippel V.", a plausible, wrong, and
# entirely silent rename. Jr/Sr/II/III/IV are two characters or more; a single
# letter, with or without its period, is an initial.
_NAME_SUFFIX = re.compile(r"^(?:Jr\.?|Sr\.?|II|III|IV)$", re.I)


def _flat(fragment):
    return " ".join(html_lib.unescape(_TAG.sub(" ", fragment or "")).split())


def flip_surname_first(name):
    """"Herlache, Thomas L. Jr." -> "Thomas L. Herlache Jr."

    The shared `clean()` flips a comma too, but it treats everything after the
    comma as given names, so a generational suffix ends up in the middle of the
    person's name. This directory prints both shapes.
    """
    if "," not in name:
        return name
    last, rest = [x.strip() for x in name.split(",", 1)]
    toks = rest.split()
    suffix = toks.pop() if toks and _NAME_SUFFIX.match(toks[-1]) else ""
    given = " ".join(toks)
    out = ("%s %s" % (given, last)).strip() if given else last
    return ("%s %s" % (out, suffix)).strip()


def read_directory_page(page, seats, spec):
    """(members_by_district, first_item, last_item, total) for one page."""
    pager = _PAGER.search(_flat(page))
    if not pager:
        raise RuntimeError("no pager on the page — the directory has changed shape")
    first, last, total = (int(x) for x in pager.groups())
    if total != seats:
        raise RuntimeError(
            "the directory says it holds %d supervisors and this county is entered "
            "with %d seats — one of the two has changed" % (total, seats))

    out, addresses = {}, 0
    for title_frag, list_frag in _ENTRY.findall(page):
        title = _flat(title_frag)
        m = DIST.search(title)
        if not m:
            continue
        district = int(m.group(1))
        if not 1 <= district <= seats:
            raise RuntimeError("the directory names District %d on a %d-district board"
                               % (district, seats))
        if district in out:
            raise RuntimeError("District %d appears twice on one page" % district)
        rest, role = split_role(DIST.sub(" ", title, count=1))
        if VACANT.search(rest):
            out[district] = {"name": None, "vacant": True, "role": None}
            continue
        row = {"name": flip_surname_first(rest.strip().strip("-–—").strip()),
               "vacant": False, "role": role}
        for label_frag, value_frag in _FIELD.findall(list_frag or ""):
            label = _flat(label_frag).rstrip(":").lower()
            if label == "address":
                # READ SO IT CAN BE REFUSED, never carried. Every one of these
                # is a supervisor's HOME (rural routes, "N5528 Ledgetop
                # Drive") — this fleet does not ship a home address even where
                # the county publishes one, the same call Taylor's document
                # roster records. Counting them is how the run proves it is
                # still reading the field it is declining, rather than having
                # quietly stopped seeing it.
                addresses += 1
            elif label == "email":
                mm = _MAILTO.search(value_frag)
                if mm:
                    email = html_lib.unescape(mm.group(1)).strip()
                    if email.lower().endswith(spec["email_domain"]):
                        row["email"] = email
            elif label == "phone":
                row["phone"] = _flat(value_frag)
        out[district] = row

    want = last - first + 1
    if len(out) != want:
        raise RuntimeError("the pager says items %d-%d (%d supervisors) and %d were "
                           "read" % (first, last, want, len(out)))
    if not addresses:
        raise RuntimeError("not one Address row on a page of %d supervisors — the "
                           "directory has changed shape and the field this build "
                           "deliberately drops can no longer be seen" % len(out))
    return out, first, last, total


def scrape_archive_county(spec):
    """All seats or nothing, from a paginated directory read through the Archive."""
    seats = spec["seats"]
    members, spans, stamps = {}, [], []
    for url in spec["pages"]:
        page, archived_at = fetch_page(url)
        got, first, last, _total = read_directory_page(page, seats, spec)
        for d, row in got.items():
            if d in members:
                raise RuntimeError("District %d appears on two pages" % d)
            members[d] = row
        spans.append((first, last))
        stamps.append(archived_at)
        print("    %-4s %s  items %d-%d"
              % ("live" if archived_at is None else archived_at[:8],
                 url.rsplit("/", 1)[-1][:34], first, last), file=sys.stderr)

    # THE PAGES MUST TILE THE BOARD, and be read from one moment in its life.
    covered = []
    for first, last in sorted(spans):
        covered.extend(range(first, last + 1))
    if covered != list(range(1, seats + 1)):
        raise RuntimeError("the pages fetched cover items %s of a %d-supervisor "
                           "directory — a page has been added or dropped"
                           % (sorted(spans), seats))
    # A PAGE THE COUNTY SERVED DIRECTLY COUNTS AS AGE ZERO, which is the whole
    # reason this is computed over ages rather than over the archive stamps: if
    # the block ever lifts for one request and not the next, page 1 arrives from
    # today and page 2 from the newest snapshot, and comparing only the stamps
    # would find one date, no spread, and nothing to complain about — the exact
    # straddle this gate exists to stop, wearing a fresher coat.
    ages = [0 if t is None else _snapshot_age_days(t) for t in stamps]
    spread = max(ages) - min(ages)
    if spread > PAGE_SPREAD_DAYS:
        raise RuntimeError(
            "the pages were captured %d days apart (limit %d) — a Wisconsin board "
            "is reseated every April, so a merge across that gap can pair "
            "supervisors who never sat together" % (spread, PAGE_SPREAD_DAYS))

    if set(members) != set(range(1, seats + 1)):
        missing = sorted(set(range(1, seats + 1)) - set(members))
        raise RuntimeError("resolved %d of %d districts (missing %s)"
                           % (len(members), seats, missing))
    named = [m["name"] for m in members.values() if not m["vacant"]]
    if len(set(named)) != len(named):
        dupes = sorted({n for n in named if named.count(n) > 1})
        raise RuntimeError("the same person is filed under two districts (%s)" % dupes)
    emails = sum(1 for m in members.values() if m.get("email"))
    phones = sum(1 for m in members.values() if m.get("phone"))
    if emails < spec["min_emails"]:
        raise RuntimeError("%d county e-mail addresses resolved, floor is %d"
                           % (emails, spec["min_emails"]))
    if phones < spec["min_phones"]:
        raise RuntimeError("%d phone numbers resolved, floor is %d"
                           % (phones, spec["min_phones"]))
    return {str(d): members[d] for d in sorted(members)}, stamps


# --- Adams: a roster that rides a PDF the county publishes ---------------------
# THE ONE COUNTY WHOSE MEMBER LIST IS A DOCUMENT AND STILL SCRAPES WEEKLY.
# Adams was filed under this file's "publish members as PDFs, images or prose"
# bucket, and the gaps record's `wanted` line said outright that "a district
# map, a PDF or an alphabetical list with no district column cannot be used".
# That rule is right about the first and third and WRONG ABOUT THE MIDDLE ONE,
# which is the finding: a PDF is a FORMAT, not a blocker. The question is
# whether it carries a TEXT LAYER and a district column, and Adams's carries
# both — twenty `DISTRICT <n>` headings, each with the supervisor's name, a
# county mailbox and a phone (the Menard lesson in Illinois, one state over:
# look for the text layer before reaching for the raster methods).
#
# NOTHING HERE IS HAND-CARRIED, which is what separates this from
# DOCUMENT_ROSTERS below. The county clerk's "2026 Public Directory" is linked
# as `County Directory` from the county's own site, and both hops are open to
# an ordinary client: www.co.adams.wi.us answers 200, and the Drive file it
# points at downloads unauthenticated. So the run RESOLVES THE LINK EVERY WEEK
# rather than pinning a file id — the clerk republishes the directory under a
# NEW Drive id each edition (this one is dated 28 August 2026 on its own cover),
# and a pinned id would go on serving the superseded edition forever with no
# error, which is the Socrata-dataset failure this project already guards
# elsewhere. The link text is the contract; if it moves, the county fails its
# guard and is skipped for that run, which is a page to re-read, not a flake.
#
# A TRAP ON THIS HOST, recorded because it defeats the obvious check: it is a
# Google Sites site, and a MISSING page answers HTTP 404 with a full 259 KB of
# site chrome. A probe that reads the body length, or that follows redirects
# and looks for content, calls that page healthy. Check the STATUS.
#
# THE DISTRICT MAILBOX IS THE WITNESS, and it is why this county needs no
# pinned reading direction like the HTML ones above. Every supervisor's contact
# line carries `district<n>@co.adams.wi.us` (six of the twenty punctuate it
# `district.<n>@`), so the document states each seat's number a SECOND time, in
# a string the layout engine cannot reorder. The parser reads the number from
# the heading and asserts the mailbox agrees — the before/after ambiguity that
# yields "a full, plausible, entirely wrong roster" on the page-scraped
# counties cannot survive that check.
#
# THE STREET ADDRESSES ARE DELIBERATELY NOT CARRIED, the same rule Taylor's
# entry states below: they are supervisors' homes, and a home address never
# ships even where the source publishes it. Name, county mailbox and phone are
# official contact details and do.
PDF_COUNTIES = [
    {
        "fips": "55001", "name": "Adams", "seats": 20,
        # the page that LINKS the directory, and the page a reader is sent to:
        # the names are published in a document, and this is where the county
        # publishes the document
        "page": "https://www.co.adams.wi.us/government/county-board",
        "source_url": "https://www.co.adams.wi.us/government/county-board",
        "link_text": "County Directory",
        "mailbox": r"district\.?(\d{1,2})@co\.adams\.wi\.us",
    },
]

# a template, not a pattern: the link TEXT is what identifies the document, so
# it is escaped in per county rather than baked in here
DRIVE_LINK = (r'href="(https://drive\.google\.com/file/d/([A-Za-z0-9_-]{20,})'
              r'/[^"]*)"[^>]*>\s*%s\s*<')
DIST_HEAD = re.compile(r"^\s*DISTRICT\s+(\d{1,2})\s*$")
# "608-547-2688", and Adams prints one as "715-781- 0354" — a space the
# extractor keeps and a reader never sees
PDF_PHONE = re.compile(r"\b(\d{3})[-\s.]\s?(\d{3})[-\s.]\s?(\d{4})\b")
# "Jerry Poehler, 1st Vice Chair" / "Rick Pease, County Board Chair"
PDF_ROLE = re.compile(
    r",\s*((?:County\s+Board\s+)?(?:(?:1st|2nd)\s+)?(?:Vice\s+)?"
    r"Chair(?:man|person|woman)?)\s*$", re.I)
# A ward-composition line ("Town of Jackson Ward 2 & Town of New Haven Ward 1")
# sits between the heading and the name and is never a person. It is matched on
# "<municipality> of" or "Ward <n>" rather than on the bare words: WARD IS ALSO
# A SURNAME, and a plain \bwards?\b would skip a supervisor named Ward on the
# walk-back and take whatever line sat above them.
PDF_WARDLINE = re.compile(r"(?i)(\b(?:towns?|cities|city|villages?)\s+of\b|\bwards?\s+\d)")


def pdf_lines(blob):
    """The directory's text, one line per printed line.

    Layout mode is required, not optional. A flattened read returns this
    document one WORD per line (its text operators are per-word), which loses
    the only thing the parser needs: that a supervisor's name, phone and
    mailbox share a printed line.
    """
    import io
    import pypdf                      # pinned in wi/scripts/requirements.txt
    reader = pypdf.PdfReader(io.BytesIO(blob))
    lines = []
    for page in reader.pages:
        lines += (page.extract_text(extraction_mode="layout") or "").split("\n")
    return [re.sub(r"\s+", " ", ln).strip() for ln in lines]


def scrape_pdf_county(spec):
    """All seats or nothing, with the county's own mailbox as the witness."""
    page = fetch(spec["page"])
    link = re.search(DRIVE_LINK % re.escape(spec["link_text"]), page)
    if not link:
        raise RuntimeError("%s: no %r link on %s — the county has moved or "
                           "renamed its directory; re-read the page"
                           % (spec["name"], spec["link_text"], spec["page"]))
    doc_url = link.group(1)
    blob = fetch_bytes("https://drive.google.com/uc?export=download&id=" + link.group(2),
                       timeout=90)[0]
    if not blob.startswith(b"%PDF"):
        raise RuntimeError("%s: %s did not return a PDF (%d bytes, starts %r) — "
                           "a Drive interstitial is the usual cause"
                           % (spec["name"], doc_url, len(blob), blob[:16]))
    lines = pdf_lines(blob)
    mailbox = re.compile(spec["mailbox"], re.I)

    heads = [(i, int(m.group(1)))
             for i, ln in enumerate(lines) for m in [DIST_HEAD.match(ln)] if m]
    # The City of Adams's aldermanic districts are in the same document under
    # the same word, but print their members on the heading's own line, so the
    # anchored heading above never matches them. Guard it anyway: a reshaped
    # document that starts matching them would otherwise ship city alderpersons
    # as county supervisors.
    if len(heads) != spec["seats"]:
        raise RuntimeError("%s: the directory carries %d 'DISTRICT n' headings "
                           "and the board seats %d — re-read %s"
                           % (spec["name"], len(heads), spec["seats"], doc_url))

    seen = [d for _, d in heads]
    if sorted(seen) != list(range(1, spec["seats"] + 1)):
        # a repeated or skipped heading would collapse in `out` below and lose a
        # seat silently; the builder's geometry check would catch it one stage
        # later, but the document is what has changed and should say so
        raise RuntimeError("%s: the directory's headings are %s, not 1..%d — "
                           "re-read %s" % (spec["name"], seen, spec["seats"], doc_url))

    out = {}
    for n, (i, district) in enumerate(heads):
        end = heads[n + 1][0] if n + 1 < len(heads) else len(lines)
        block = lines[i + 1:end]
        at = next((k for k, ln in enumerate(block) if mailbox.search(ln)), None)
        if at is None:
            raise RuntimeError("%s: district %d carries no county mailbox — the "
                               "directory has reshaped; re-read %s"
                               % (spec["name"], district, doc_url))
        m = mailbox.search(block[at])
        if int(m.group(1)) != district:
            # the document numbering itself disagrees; never guess which is right
            raise RuntimeError("%s: the heading says district %d and the mailbox "
                               "on that seat's line says %s (%s) — re-read %s"
                               % (spec["name"], district, m.group(1),
                                  m.group(0), doc_url))
        line = block[at]
        phone_m = PDF_PHONE.search(line)
        phone = "-".join(phone_m.groups()) if phone_m else None
        cut = min(phone_m.start() if phone_m else len(line), m.start())
        name = line[:cut].strip(" ,;")
        if not name:
            # Two of the twenty print the name on its own line above the
            # contact line (both carry a second phone: "608-254-5971 or
            # 608-432-1971"), so walk back past the ward composition.
            k = at - 1
            while k >= 0 and (not block[k] or PDF_WARDLINE.search(block[k])):
                k -= 1
            name = block[k].strip() if k >= 0 else ""
        role = None
        role_m = PDF_ROLE.search(name)
        if role_m:
            role = role_case(role_m.group(1))
            name = name[:role_m.start()].strip(" ,")
        name = repair(clean(name)[0])
        if not is_name(name):
            raise RuntimeError("%s: district %d resolved to %r, which does not "
                               "read as a name — re-read %s"
                               % (spec["name"], district, name, doc_url))
        row = {"name": name, "vacant": False, "role": role,
               "email": m.group(0).lower()}
        if phone:
            row["phone"] = phone
        out[str(district)] = row

    names = [r["name"] for r in out.values()]
    if len(set(names)) != len(names):
        dupes = sorted({n for n in names if names.count(n) > 1})
        raise RuntimeError("%s: the same person is filed under two districts (%s)"
                           % (spec["name"], dupes))
    return out, doc_url


# COUNTIES WHOSE ROSTER IS A TABLE THE LISTING PAGE FRAMES FROM ANOTHER HOST.
# Columbia publishes all 28 of its seats, each with its own profile page, and
# none of the five readings above can see a word of it — for two reasons that
# compound:
#
#   * THE PAGE A READER IS GIVEN CONTAINS NO SUPERVISOR. The county's
#     Supervisor Listing is a DNN shell whose whole body is an <iframe> onto
#     board.co.columbia.wi.us — a second host, unstyled, serving one table.
#     Fetching the listing page and reading its lines yields the site nav, the
#     clerk's address and nothing else; the county reads as publishing no
#     roster, which is what it had been recorded as.
#   * THE NAME IS SPLIT ACROSS TWO CELLS. The table's columns are First Name |
#     Last Name | Address & Phone | Supervisory District | wards, so no single
#     cell ever holds a whole name. `_column` pairs a bare-numeral district
#     with the nearest cell that reads as a NAME, and "Connor" alone is one
#     token where `is_name` needs two — so even pointed at the frame, the
#     column reading resolves nothing.
#
# So this route reads the TABLE rather than the text: the header row maps
# column NAMES to positions and every data row is read through that map. Read
# by position instead and a county inserting a column ships every supervisor
# under their neighbour's district — the same shifted-by-one failure the
# pinned reading directions exist to prevent, one surface over.
#
# THE FRAME HOST IS PINNED AND CHECKED. The listing page's iframe src must
# still be the host below, or the county fails loudly: a roster host the
# county has stopped pointing at is not the county's roster any more, and
# would go on scraping clean for as long as it stayed up. `source_url` is the
# LISTING page all the same — it is where a reader confirms the name, and the
# frame alone is a bare table with no county around it.
#
# WHAT IS DELIBERATELY NOT CARRIED. The Address & Phone column is supervisors'
# HOME addresses ("P.O. Box 81", "W12974 State Road 188") with a home or cell
# number beside them; a home address never ships in this fleet even where the
# source publishes it (the Taylor rule), and the phone beside it is not an
# office line. The "Email" link per row is a CONTACT FORM on the county's
# site, not an address, so it cannot ship as one either.
FRAMED_TABLE_COUNTIES = [
    {
        "fips": "55021", "name": "Columbia", "seats": 28,
        "page": ("https://www.co.columbia.wi.us/columbiacounty/countyboard/"
                 "Board-of-Supervisors/Supervisor-Listing"),
        "frame": "https://board.co.columbia.wi.us/",
        # header text -> what it holds. Matched case-insensitively on the
        # header row's own cells; a header that stops appearing fails the
        # county rather than shifting it.
        "columns": {"district": "supervisory district",
                     "first": "first name", "last": "last name"},
        # The chair and both vice chairs are named in a footer block of their
        # own, each linked to their own Supervisor-Profile — so the join is on
        # the COUNTY'S OWN supervisor id, not on a name. That is the strongest
        # form of this join in the file: `attach_officer_roles` has to match
        # typography because its counties publish nothing better.
        "officers": {"heading": "Columbia County Board Chairs", "window": 2000},
    },
]

FRAME_SRC = re.compile(r'(?is)<iframe\b[^>]*\bsrc\s*=\s*["\']?([^"\'\s>]+)')
TABLE_ROW = re.compile(r"(?is)<tr\b[^>]*>(.*?)</tr>")
# `<t([dh])\b` and not `<t[dh]`: the latter also matches <thead>, which would
# make the whole header section read as one giant cell.
TABLE_CELL = re.compile(r"(?is)<t([dh])\b[^>]*>(.*?)</t\1>")
PROFILE_ID = re.compile(r"(?i)supervisorid/(\d+)")
_CELL_TAGS = re.compile(r"(?s)<[^>]+>")


def cell_text(fragment):
    return " ".join(html_lib.unescape(_CELL_TAGS.sub(" ", fragment)).split())


def _row_cells(row_html):
    """[(kind, inner_html)] for one <tr>, kind being 'd' (td) or 'h' (th)."""
    return TABLE_CELL.findall(row_html)


def _host(url):
    return url.split("//", 1)[-1].split("/", 1)[0].lower()


def framed_table_officers(page_html, spec, by_id, county):
    """District -> role, joined on the county's own supervisor id.

    Never fails the county: a footer that has moved costs the CHAIR MARKING,
    and a county with no marked chair makes the officer builder withhold the
    Blue Book's chair with its reason stated rather than name the wrong
    person. Losing 28 supervisors over a footer would be the worse trade.
    """
    conf = spec.get("officers")
    if not conf:
        return {}
    # re.search rather than str.lower().find(): lower() is not
    # length-preserving for every Unicode code point, and an index taken from
    # the folded copy can land mid-tag in the original.
    at = re.search(re.escape(conf["heading"]), page_html, re.I)
    if not at:
        print("  note %-12s officers block %r is gone — no chair marked this run"
              % (county, conf["heading"]), file=sys.stderr)
        return {}
    block = page_html[at.start():at.start() + conf["window"]]
    pattern = re.compile(r'(?is)supervisorid/(\d+)[^>]*>\s*([^<]{2,60}?)\s*</a>\s*,\s*(%s)\b'
                          % _ROLE)
    roles = {}
    for sid, named, role in pattern.findall(block):
        district = by_id.get(sid)
        if district is None:
            print("  note %-12s officer %r (id %s) is not on the roster — role "
                  "%r not attached" % (county, named, sid, role), file=sys.stderr)
            continue
        if district in roles:
            print("  note %-12s district %s is named twice in the officers block "
                  "— role %r not attached" % (county, district, role), file=sys.stderr)
            continue
        roles[district] = role_case(role)
        print("  role %-12s district %s: %s -> %s"
              % (county, district, named, roles[district]), file=sys.stderr)
    if not roles:
        print("  note %-12s officers block named nobody on the roster"
              % county, file=sys.stderr)
    return roles


def scrape_framed_table_county(spec):
    """A roster read as a TABLE out of the page the listing page frames."""
    name, seats = spec["name"], spec["seats"]
    page_html = fetch(spec["page"])
    framed = [u for u in FRAME_SRC.findall(page_html) if u.startswith("http")]
    if not any(_host(u) == _host(spec["frame"]) for u in framed):
        raise RuntimeError(
            "%s: the listing page no longer frames %s (it frames %s) — the roster "
            "has moved, and scraping the old host would go on succeeding"
            % (name, _host(spec["frame"]), [_host(u) for u in framed] or "nothing"))

    rows = TABLE_ROW.findall(fetch(spec["frame"]))
    header = None
    for row in rows:
        cs = _row_cells(row)
        if cs and all(kind == "h" for kind, _ in cs):
            header = {cell_text(c).lower(): i for i, (_, c) in enumerate(cs)}
            break
    if header is None:
        raise RuntimeError("%s: the roster table has no header row to read its "
                           "columns from" % name)
    try:
        idx = {k: header[v] for k, v in spec["columns"].items()}
    except KeyError as missing:
        raise RuntimeError("%s: the roster table no longer has a %s column (it has "
                           "%s) — re-read it before shipping"
                           % (name, missing, sorted(header)))

    found, by_id = {}, {}
    for row in rows:
        cells = [c for kind, c in _row_cells(row) if kind == "d"]
        if not cells:
            continue                        # the header row
        if len(cells) <= max(idx.values()):
            raise RuntimeError("%s: a roster row has %d cells where the header "
                               "declares at least %d — the table has reshaped"
                               % (name, len(cells), max(idx.values()) + 1))
        m = BARE_NUM.match(cell_text(cells[idx["district"]]))
        if not m:
            raise RuntimeError("%s: row %r carries no district number in its "
                               "district column" % (name, cell_text(cells[idx["first"]])))
        d = int(m.group(1))
        whole = " ".join(cell_text(cells[idx[k]]) for k in ("first", "last")).strip()
        if not _reads_as_name(whole):
            raise RuntimeError("%s: district %d's name cells read as %r, which is "
                               "not a name" % (name, d, whole))
        if d in found:
            raise RuntimeError("%s: district %d appears twice in the table" % (name, d))
        found[d] = clean(whole)
        sid = PROFILE_ID.search(cells[idx["last"]]) or PROFILE_ID.search(cells[idx["first"]])
        if sid:
            by_id[sid.group(1)] = str(d)

    if set(found) != set(range(1, seats + 1)):
        missing = sorted(set(range(1, seats + 1)) - set(found))
        raise RuntimeError("%s: the table resolved %d of %d districts (missing %s)"
                           % (name, len(found), seats, missing))
    names = [v[0] for v in found.values()]
    if len(set(names)) != len(names):
        dupes = sorted({n for n in names if names.count(n) > 1})
        raise RuntimeError("%s: the same person is filed under two districts (%s)"
                           % (name, dupes))

    roles = framed_table_officers(page_html, spec, by_id, name)
    out = {}
    for d in range(1, seats + 1):
        member, role = found[d]
        out[str(d)] = {"name": member, "vacant": False,
                        "role": role or roles.get(str(d))}
    return out


def _fetch_json(url):
    req = urllib.request.Request(url, headers=headers_for(url))
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, timeout=45, context=ctx) as r:
        return json.load(r)


def _fold_person(name):
    """First + last token, diacritics stripped: the layer prints
    'Caroline Gómez-Tom' and 'Sheldon A. Wasserman' where Legistar prints
    'Caroline Gomez-Tom' and 'Sheldon Wasserman' — same people, three
    styling axes (accents, middle initials, hyphens), so the witness match
    folds all three rather than failing on typography."""
    import unicodedata
    flat = unicodedata.normalize("NFKD", str(name))
    flat = "".join(ch for ch in flat if not unicodedata.combining(ch))
    toks = [t for t in re.split(r"[^A-Za-z]+", flat.lower()) if len(t) > 1]
    if not toks:
        return ""
    return toks[0] + "|" + toks[-1]


# --- the district-key witness for a roster that rides a county's own layer ----
#
# A ROSTER KEYED BY DISTRICT NUMBER IS ONLY AS GOOD AS THE TWO PUBLISHERS
# AGREEING WHAT THAT NUMBER MEANS ON THE GROUND. The card decides which
# district a reader is in from the SHIPPED LTSB geometry and then names that
# district's supervisor from the county. Where the county's own map draws a
# district differently, those two steps answer about different ground, and the
# card names somebody who does not represent the reader.
#
# Lincoln is why this exists and it is not hypothetical: 4,000 random points
# inside that county put 97.90% in the same-numbered district on both
# publishers' maps, and the whole of the remainder is one lobe — Town of
# Merrill ward 2, which LTSB files in supervisory district 21 and the county's
# own layer draws in district 9. Both agree it is that ward; they disagree
# about its district. LTSB is internally consistent (its ward file and its
# district polygons agree), and the county's ward layer carries no district
# field and cannot arbitrate. So the disagreement stands, and the two districts
# it touches are WITHHELD rather than preferred.
#
# THE SAMPLE IS PER DISTRICT AND THE SHIPPED FILE IS THE PROBE SOURCE, so this
# costs ONE request: the county's layer generalised to ~50 m, which is far
# finer than the disagreement it is looking for. Points come from the LTSB
# districts already on disk. A district is disputed when fewer than
# DISTRICT_AGREE_MIN of its probes land in the same-numbered county district;
# boundary noise moves one or two probes, a redrawn boundary moves most.
DISTRICT_PROBES = 40
DISTRICT_AGREE_MIN = 0.90


def _ring_hit(pt, ring):
    x, y = pt
    hit = False
    for i in range(len(ring)):
        x1, y1 = ring[i][0], ring[i][1]
        x2, y2 = ring[(i + 1) % len(ring)][0], ring[(i + 1) % len(ring)][1]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            hit = not hit
    return hit


def _geo_parts(geom):
    """GeoJSON polygon parts — a MultiPolygon's parts are NOT one polygon's holes.

    Lincoln has two multipart districts (17 and 21) and reading their parts as
    holes flips the answer for exactly the district the witness is about.
    """
    if geom["type"] == "Polygon":
        return [geom["coordinates"]]
    return geom["coordinates"]


def _geo_contains(pt, geom):
    for poly in _geo_parts(geom):
        if _ring_hit(pt, poly[0]) and not any(_ring_hit(pt, h) for h in poly[1:]):
            return True
    return False


def district_geometry_witness(fips, county, layer, seats):
    """{disputed district numbers} — the county's own map against LTSB's.

    A FETCH FAILURE IS NOT A DISAGREEMENT: an unreachable witness says nothing,
    so it stands aside and the caller ships unwitnessed with the log saying so.
    A witness that RUNS and finds a district redrawn returns it, and the caller
    withholds that seat rather than choosing between two publishers.
    """
    try:
        shipped = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "..", "data", "app",
                               "county-supervisory-districts.json")
        with open(shipped) as f:
            ltsb = {int(x["properties"]["SUPERID"]): x["geometry"]
                    for x in json.load(f)["features"]
                    if x["properties"]["CNTY_FIPS"] == fips}
        data = _fetch_json(layer + "/query?where=1%3D1&outFields=" +
                           "SuperID_Numeric&returnGeometry=true&outSR=4326"
                           "&maxAllowableOffset=0.0005&f=geojson")
        cty = {int(f["properties"]["SuperID_Numeric"]): f["geometry"]
               for f in data.get("features") or []}
        if not ltsb or not cty:
            raise RuntimeError("no districts on one side")
    except Exception as e:          # noqa: BLE001 - the witness, never the source
        print("  WITNESS SKIPPED %-9s district geometry unreachable (%s) — the "
              "roster ships unwitnessed this run" % (county, e), file=sys.stderr)
        return set()
    if sorted(ltsb) != sorted(cty) != list(range(1, seats + 1)):
        raise RuntimeError(
            "%s: the shipped map draws districts %s and the county's own layer "
            "draws %s — one of the two has been redistricted and neither is "
            "guessed at" % (county, sorted(ltsb), sorted(cty)))

    rng = random.Random(20260902)
    disputed, worst = set(), {}
    for d, geom in sorted(ltsb.items()):
        xs = [c[0] for p in _geo_parts(geom) for r in p for c in r]
        ys = [c[1] for p in _geo_parts(geom) for r in p for c in r]
        got = agree = 0
        tries = 0
        while got < DISTRICT_PROBES and tries < DISTRICT_PROBES * 400:
            tries += 1
            pt = (rng.uniform(min(xs), max(xs)), rng.uniform(min(ys), max(ys)))
            if not _geo_contains(pt, geom):
                continue
            got += 1
            if _geo_contains(pt, cty[d]):
                agree += 1
        if not got:
            continue                # a district too thin to sample says nothing
        share = float(agree) / got
        worst[d] = share
        if share < DISTRICT_AGREE_MIN:
            disputed.add(d)
    overall = sum(worst.values()) / len(worst) if worst else 0.0
    print("  witness %-12s %d/%d districts drawn the same by the county and the "
          "state (mean agreement %.1f%%)"
          % (county, seats - len(disputed), seats, 100.0 * overall), file=sys.stderr)
    for d in sorted(disputed):
        print("  DISPUTED %-9s district %d: only %.0f%% of its ground is district "
              "%d on the county's own map — the seat is WITHHELD, not preferred"
              % (county, d, 100.0 * worst[d], d), file=sys.stderr)
    return disputed


def scrape_arcgis_county(spec):
    """District -> member rows read as ATTRIBUTES off the county's own layer."""
    fields = spec["fields"]
    out_fields = ",".join(v for v in fields.values())
    data = _fetch_json(spec["layer"] + "/query?where=1%3D1&outFields=" +
                       out_fields + "&returnGeometry=false&f=json")
    feats = data.get("features") or []
    rows = {}
    for f in feats:
        a = f.get("attributes") or {}
        d = a.get(fields["district"])
        member = a.get(fields["name"])
        if d is None or not member:
            continue
        d = int(str(d).strip())
        member = str(member).strip()
        role = None
        # Milwaukee packs the officer's ROLE into the name field for its two
        # officers ("Chairwoman Marcelia Nicholson-Bovell") — the measured
        # trap; the role moves to its own field, never ships inside a name.
        rm = re.match(r"^(Chairwoman|Chairman|Chairperson|Chair|Vice[- ]?Chair(?:woman|man)?|1st Vice[- ]?Chair(?:woman|man)?|2nd Vice[- ]?Chair(?:woman|man)?)\s+(.+)$", member, re.I)
        if rm:
            role = rm.group(1).strip()
            member = rm.group(2).strip()
        email = a.get(fields.get("email")) if fields.get("email") else None
        if email:
            # Milwaukee packs its addresses as "mailto:x@y?subject=" — unwrap
            email = re.sub(r"^mailto:", "", str(email)).split("?")[0].strip() or None
        entry = {"name": member, "vacant": False, "role": role}
        if email:
            entry["email"] = email
        if fields.get("phone") and a.get(fields["phone"]):
            tel = re.search(r"(\d{3})\D*(\d{3})\D*(\d{4})", str(a[fields["phone"]]))
            if tel:
                entry["phone"] = "-".join(tel.groups())
        if fields.get("url") and a.get(fields["url"]):
            entry["url"] = str(a[fields["url"]]).strip()
        rows[d] = entry
    if set(rows) != set(range(1, spec["seats"] + 1)):
        missing = sorted(set(range(1, spec["seats"] + 1)) - set(rows))
        raise RuntimeError("%s: layer resolved %d of %d districts (missing %s)"
                           % (spec["name"], len(rows), spec["seats"], missing))
    # THE DISTRICT KEY, WHERE THE COUNTY PUBLISHES ITS OWN MAP OF IT. A seat
    # the two publishers draw differently is WITHHELD — see
    # district_geometry_witness() for Lincoln's measured lobe.
    if spec.get("district_witness"):
        for d in district_geometry_witness(spec["fips"], spec["name"], spec["layer"],
                                           spec["seats"]):
            rows[d] = {"name": None, "vacant": False, "role": None,
                       "withheld": True, "withheld_why": spec["district_witness"]}
    witness = spec.get("witness")
    if witness:
        recs = _fetch_json("https://webapi.legistar.com/v1/%s/officerecords"
                           "?$filter=OfficeRecordBodyId+eq+%d&$top=400"
                           % (witness["client"], witness["body_id"]))
        # end-date filtering is CLIENT-side: the server ignores date filters,
        # and the cutoff is TODAY — an April term-end must not count as current
        today = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())
        current = {_fold_person(r["OfficeRecordFullName"]) for r in recs
                   if (r.get("OfficeRecordEndDate") or "9999") > today}
        layer_names = {_fold_person(v["name"]) for v in rows.values() if v.get("name")}
        if layer_names != current:
            raise RuntimeError(
                "%s: the GIS layer and the Legistar witness disagree on the bench "
                "(layer-only: %s; legistar-only: %s) — do not ship either side"
                % (spec["name"], sorted(layer_names - current),
                   sorted(current - layer_names)))
    return {str(d): rows[d] for d in sorted(rows)}


# COUNTIES WHOSE ROSTER IS A PAGINATED CONSTITUENT DIRECTORY, NOT A PAGE OF TEXT.
#
# DODGE (2026-08-29). Its board page publishes all 33 seats district-keyed
# ("County Board Supervisor, District 32") in a Finalsite constituent
# directory, and the whole county was recorded here as "publishes prose" until
# a reader reported that co.dodge.wi.us had moved. That host was answering
# HTTP 200 with a 261-byte "This site has permanently moved" stub, so a sweep
# reading STATUS CODES could not tell a county that publishes nothing from one
# that published a forwarding note.
#
# THE DIRECTORY PAGINATES AT TWELVE, which is why this is a separate strategy
# and not a row in COUNTIES. Three things about it were measured rather than
# assumed, and each was wrong on the first guess:
#
#   * `?const_page=2` ON THE PAGE ITSELF IS DECORATION. The server returns page
#     one for every value of it, so a single fetch of the members URL sees 12
#     of 33 — and 12 seats of a 33-seat board is exactly what the
#     all-seats-or-nothing rule exists to refuse.
#   * The pagination works on the ELEMENT endpoint (/fs/elements/<id>) and
#     ONLY when `const_search_group_ids` rides along. Without the group id that
#     endpoint also returns page one, silently and with a 200.
#   * NEITHER ID IS PINNED. Both are discovered from the members page on every
#     run — the directory element by its own `fsConstituent fsDirectory` class,
#     the group id from the county's own search form — so a site rebuild that
#     renumbers elements keeps working, and a page carrying two directories
#     fails loudly instead of scraping whichever came first.
#
# THE E-MAILS ARE OBFUSCATED and would otherwise have shipped as nothing at
# all: each address is written as a reversed-string JavaScript call
# (`FS.util.insertEmail(id, "su.iw.egdod.oc", "23tcirtsid")` is
# district32@co.dodge.wi.us). That is the Brown County shape from Illinois —
# seven addresses emptied silently when a county switched on Cloudflare's
# mailto obfuscation — so it is decoded, never dropped.
#
# THEY ARE ALSO DERIVABLE, AND ARE NOT DERIVED. Every address is
# district<N>@co.dodge.wi.us, so the district number in the address is a free
# CHECK on the row it was read from: an address whose number disagrees with
# its own row means the page has reshuffled under the parser, and the county
# fails rather than shipping a supervisor someone else's contact. An address
# that is not a district alias at all (a personal one) ships as published.
#
# The mail domain is the OLD one and that is correct: co.dodge.wi.us carries
# live MX and is what the county's own clerk page still prints. A web domain
# and a mail domain move separately.
CONSTITUENT_COUNTIES = [
    {
        "fips": "55027", "name": "Dodge", "seats": 33,
        "page_url": "https://www.co.dodge.wi.gov/government/county-board/members",
        "source_url": "https://www.co.dodge.wi.gov/government/county-board/members",
    },
]
_DIR_ELEMENT = re.compile(r'<div class="fsElement fsConstituent fsDirectory[^"]*" id="fsEl_(\d+)"')
_GROUP_ID = re.compile(r'name="const_search_group_ids" value="(\d+)"')
_PAGE_LABEL = re.compile(r'fsPaginationLabel">\s*showing\s+(\d+)\s*-\s*(\d+)\s+of\s+(\d+)')
_ITEM = re.compile(r'<div class="fsConstituentItem"(.*?)(?=<div class="fsConstituentItem"|\Z)', re.S)
_FULL_NAME = re.compile(r'class="fsFullName">\s*(?:<[^>]*>\s*)*([^<]+?)\s*</a>', re.S)
_TITLES = re.compile(r'<div class="fsTitles">(.*?)</div>', re.S)
# FS.util.insertEmail(elementId, reversedDomain, reversedLocalPart, ...)
_INSERT_EMAIL = re.compile(r'insertEmail\(\s*"[^"]*"\s*,\s*"([^"]+)"\s*,\s*"([^"]+)"')
_DISTRICT_ALIAS = re.compile(r"^district(\d{1,2})$", re.I)
CONSTITUENT_PAGE_CAP = 12          # 12 per page; a 33-seat board needs 3


def _constituent_items(page_html):
    """-> {district: {'name': str, 'email': str|None}} for ONE fetched page."""
    out = {}
    for m in _ITEM.finditer(page_html):
        chunk = m.group(1)
        nm = _FULL_NAME.search(chunk)
        ti = _TITLES.search(chunk)
        if not nm or not ti:
            continue
        titles = " ".join(html_lib.unescape(_TAG.sub(" ", ti.group(1))).split())
        dm = DIST.search(titles)
        if not dm:
            continue
        row = {"name": " ".join(html_lib.unescape(nm.group(1)).split()), "email": None}
        em = _INSERT_EMAIL.search(chunk)
        if em:
            row["email"] = "%s@%s" % (em.group(2)[::-1], em.group(1)[::-1])
        out[int(dm.group(1))] = row
    return out


def _constituent_officers(page_html, county):
    """-> {district: role}. The county states the DISTRICT beside each officer,
    so the join is on the file's own key rather than on a name — which is the
    stronger join and is also the only one available here: the officer cards
    say "Dave Frohling" where the directory says "David Frohling"."""
    out = {}
    for sec in re.findall(r'<section class="fsElement fsContent"[^>]*>(.*?)</section>',
                          page_html, re.S):
        title = re.search(r'<h2 class="fsElementTitle"[^>]*>(.*?)</h2>', sec, re.S)
        if not title:
            continue
        role = " ".join(html_lib.unescape(_TAG.sub(" ", title.group(1))).split())
        if not re.fullmatch(_ROLE, role, re.I):
            continue
        dm = DIST.search(" ".join(_TAG.sub(" ", sec).split()))
        if not dm:
            print("  note %-12s officer block %r names no district — not attached"
                  % (county, role), file=sys.stderr)
            continue
        d = int(dm.group(1))
        if d in out:
            raise RuntimeError("%s: two officer blocks claim district %d" % (county, d))
        out[d] = role_case(role)
    return out


def scrape_constituent_county(spec):
    """All seats or nothing, read from a paginated Finalsite directory."""
    county = spec["name"]
    page = fetch(spec["page_url"])
    els = sorted(set(_DIR_ELEMENT.findall(page)))
    gids = sorted(set(_GROUP_ID.findall(page)))
    if len(els) != 1 or len(gids) != 1:
        raise RuntimeError("%s: the page carries %d constituent director(ies) and %d "
                           "search group(s) — expected one of each; re-read it before "
                           "moving this entry" % (county, len(els), len(gids)))
    root = spec["page_url"].split("/", 3)
    base = "%s//%s/fs/elements/%s" % (root[0], root[2], els[0])
    label = _PAGE_LABEL.search(page)
    if not label:
        raise RuntimeError("%s: the directory states no total — it may have stopped "
                           "paginating; re-read it" % county)
    total = int(label.group(3))
    if total != spec["seats"]:
        raise RuntimeError("%s: the directory holds %d constituents and the board seats "
                           "%d — one of the two has changed"
                           % (county, total, spec["seats"]))

    found = {}
    pages = -(-total // CONSTITUENT_PAGE_CAP)
    for n in range(1, pages + 1):
        got = _constituent_items(
            fetch("%s?const_page=%d&const_search_group_ids=%s" % (base, n, gids[0])))
        if not got:
            raise RuntimeError("%s: page %d of %d parsed no members — the group id no "
                               "longer paginates this directory" % (county, n, pages))
        for d, row in got.items():
            if d in found and found[d] != row:
                raise RuntimeError("%s: district %d appears twice with different "
                                   "members (%r, %r)" % (county, d, found[d], row))
            found[d] = row
    want = set(range(1, spec["seats"] + 1))
    if set(found) != want:
        raise RuntimeError("%s: the directory resolved %d of %d districts (missing %s)"
                           % (county, len(found), spec["seats"],
                              sorted(want - set(found))))
    names = [r["name"] for r in found.values()]
    if len(set(names)) != len(names):
        dupes = sorted({n for n in names if names.count(n) > 1})
        raise RuntimeError("%s: the same person is filed under two districts (%s)"
                           % (county, dupes))

    out = {}
    for d in sorted(found):
        row = {"name": found[d]["name"], "vacant": False, "role": None}
        email = found[d]["email"]
        if email:
            alias = _DISTRICT_ALIAS.match(email.split("@")[0])
            if alias and int(alias.group(1)) != d:
                raise RuntimeError(
                    "%s: district %d's row carries %s — the address names another "
                    "district, so the page has reshuffled under this parser"
                    % (county, d, email))
            row["email"] = email
        out[str(d)] = row

    for d, role in sorted(_constituent_officers(page, county).items()):
        if str(d) not in out:
            raise RuntimeError("%s: an officer block names district %d, which the "
                               "directory does not" % (county, d))
        listed = out[str(d)]["name"]
        block_name = None
        for sec in re.findall(r'<section class="fsElement fsContent"[^>]*>(.*?)</section>',
                              page, re.S):
            if not re.search(r"District\s*%d\b" % d, _TAG.sub(" ", sec)):
                continue
            h5 = re.search(r"<h5[^>]*>(.*?)(?:<br|</h5>)", sec, re.S)
            if h5:
                block_name = " ".join(html_lib.unescape(_TAG.sub(" ", h5.group(1))).split())
            break
        if block_name and _surname(block_name) != _surname(listed):
            raise RuntimeError(
                "%s: the %s block names %r and the directory puts %r in district %d — "
                "the officer cards and the member list disagree, ship neither"
                % (county, role, block_name, listed, d))
        if block_name and block_name != listed:
            print("  note %-12s district %s: officer card says %r, member list says %r "
                  "— shipping the member list" % (county, d, block_name, listed),
                  file=sys.stderr)
        out[str(d)]["role"] = role
        print("  role %-12s district %s: %s -> %s" % (county, d, listed, role),
              file=sys.stderr)
    return out

# --- COUNTIES WHOSE ROSTER IS A DOCUMENT THIS FILE FETCHES AND WITNESSES ------
# NOT DOCUMENT_ROSTERS, which is the OPPOSITE arrangement: that table carries a
# roster an operator read once in a browser because a captcha fronts the host,
# marks every record `carried_from_document` and never re-reads it. These entries
# are FETCHED FRESH EVERY RUN and cross-checked against a second county surface,
# so they carry no such flag and no such caveat. Two routes, one word, opposite
# currency claims — keep them apart.
#
# Kenosha's Clerk publishes an annual Directory of Public Officials — a 107-page
# PDF whose County Board section prints each district beside its supervisor's
# NAME, PHONE and E-MAIL, and marks the Chair and Vice-Chair on their own rows.
# Only Taylor's carried directory (DOCUMENT_ROSTERS) is as rich; no county whose
# roster comes off a PAGE publishes contact for its board at all.
#
# A document is a weaker thing to depend on than a page, so it ships only under
# a witness: the county's own board page carries the same 23 districts and the
# same 23 names, read with the plain `after` reading every page county uses.
# ALL 23 MUST AGREE OR THE COUNTY SHIPS NOTHING — the same all-or-nothing rule
# scrape_county holds, with the two surfaces checking each other rather than a
# reading direction checking itself.
#
# THE ROLES ARE HELD TO A SEPARATE, WEAKER GATE, and that split is deliberate.
# A directory is printed once a year; boards elect their chair every April, so
# the document is exactly the surface that can be a year stale about who chairs
# it — and the county card's board chair is reconciled against this roster, so a
# stale role here would supersede the Blue Book with something older still. The
# board page states its leadership in a sentence of prose ("Supervisor X is the
# Chairman and Supervisor Y is the Vice Chairman for the ... term"), so the
# roles ship only when that sentence names the same two people. If the sentence
# is reworded past this reader, the NAMES still ship and the roles are withheld
# with the reason printed — a re-worded sentence must not cost a county its
# whole roster, and an unwitnessed chair must not reach a card.
#
# THE PROFILE LINKS ARE PAIRED BY BLOCK, NOT BY POSITION. Each supervisor is one
# <p> on the board page holding one /Directory.aspx?EID=<n> link, the district
# and the name, so the link is read from the same block as the district it
# belongs to and a seat whose block does not resolve simply gets no link. Two
# reasons not to do it any other way, both measured on this page: District 7 is
# marked up as TWO anchors to one EID either side of a <br> where every other
# seat is one anchor, so an anchor-per-supervisor rule finds 22 of 23; and the
# image alt attributes — the obvious second pairing — carry the county's own
# typos, spelling District 9 "John Morissey" and District 23 "Aaron Karrow"
# against the visible text's "Morrissey" and "Karow". THE ALT TEXT WOULD HAVE
# WITNESSED THE DISTRICT AND CORRUPTED THE NAME.
WITNESSED_DOCUMENT_COUNTIES = [
    {
        "fips": "55059", "name": "Kenosha", "seats": 23,
        # STABLE county page id -> 302 -> the current DocumentCenter edition;
        # never the /DocumentCenter/View/<edition>/ address, which freezes.
        "document": "https://www.kenoshacountywi.gov/1018/County-Directory-PDF",
        # the document's board section, sliced between two headings it prints
        # exactly once each in this order — "BOARD OF SUPERVISORS" occurs again
        # inside "COMMITTEES OF THE KENOSHA COUNTY BOARD OF SUPERVISORS", which
        # is precisely where the section has to stop: the committee lists name
        # supervisors as committee CHAIRS, a role that is not the board's.
        "section": ("BOARD OF SUPERVISORS", "COMMITTEES OF THE"),
        "witness": "https://www.kenoshacountywi.gov/113/County-Board-of-Supervisors",
        # the reader lands on the page, not on a 900 KB PDF; both publish every
        # name the card shows
        "source_url": "https://www.kenoshacountywi.gov/113/County-Board-of-Supervisors",
        "profile_prefix": "https://www.kenoshacountywi.gov",
    },
]

# "1. William Grady ....... 262-652-2020" for districts 1-14 and "15 Dave
# Geertsen ....... 262-515-3334" for 15-23: THE SAME DOCUMENT NUMBERS ITS ROWS
# TWO WAYS, so the period is optional or a reader gets 14 of 23. The leader run
# is optional too, and is not always dots — two rows use U+2026 ellipses with no
# space before the phone at all ("7. Daniel Gaschke…………262-902-7028").
DOC_ROW = re.compile(r"^(\d{1,2})[.)]?\s+(.+?)\s*"
                     r"(\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})\s*$")
DOC_LEADER_TAIL = re.compile(r"[\s.…]+$")
DOC_EMAIL = re.compile(r"(?i)^e-?\s?mail:?\s*(\S+@\S+)$")
# "Supervisor Mark Nordigian is the Chairman and Supervisor John Franco is the
# Vice Chairman for the 2026-2028 County Board term."
LEADERSHIP = re.compile(
    r"(?i)supervisor\s+(.+?)\s+is\s+the\s+chair(?:man|person|woman)?\b"
    r".{0,80}?supervisor\s+(.+?)\s+is\s+the\s+vice[\s-]?chair(?:man|person|woman)?\b")
# one supervisor's block on the board page: a <p> holding exactly one profile
# link, the district and the name
DOC_BLOCK = re.compile(r"(?is)<p\b[^>]*>(.*?)</p>")
DOC_PROFILE = re.compile(r"(?i)href=\"(/Directory\.aspx\?EID=\d+)\"")
DOC_DISTNAME = re.compile(r"(?i)^District\s*(\d{1,2})\s+(.+)$")


def document_rows(pdf_bytes, section):
    """District -> {name, role, phone, email} out of the Clerk's directory.

    A row needs a PHONE to be recognised, which is how the directory writes
    every seat it fills, so a VACANT seat would not parse and its district
    would go missing — taking the whole county out through the count gate
    below rather than shipping 22 of 23. That is deliberate and it is the same
    all-or-nothing rule scrape_county holds, but it is NOT the vacancy handling
    the page counties have: this county has no vacancy today, and the day it
    has one the run fails naming the missing district, which is a person
    reading the directory rather than a silent short roster.
    """
    # IMPORTED HERE, NOT AT MODULE SCOPE, and the difference is a CI failure.
    # It sat at the top of this file on the reasoning that
    # scripts/validate_workflow_deps.py reads imports and would fail the merge
    # if the weekly workflow stopped installing pypdf. It reads this one too —
    # that validator folds a script's FUNCTION-LOCAL imports in for the entry
    # point a workflow actually executes, which this file is, so the gate is
    # unchanged. What module scope additionally did was charge the dependency to
    # everything that merely IMPORTS this module: the county-clerk workflow,
    # which wants four regexes from here, and smoke-test.yml's stdlib-only
    # `build_wi_county_board_directory.py --check`, which imports COUNTIES to
    # cross-check hosts and died on `No module named pypdf`. A lazy import costs
    # an importer nothing, which is the whole reason the validator draws the
    # line where it does.
    from pypdf import PdfReader           # noqa: PLC0415 — see above
    reader = PdfReader(io.BytesIO(pdf_bytes))
    whole = "\n".join(page.extract_text() or "" for page in reader.pages)
    try:
        start = whole.index(section[0])
        end = whole.index(section[1])
    except ValueError as e:
        raise RuntimeError("the directory no longer prints %r/%r — re-read it "
                           "before shipping (%s)" % (section[0], section[1], e))
    if not start < end:
        raise RuntimeError("the directory's %r heading now follows %r — the "
                           "board section is not where this reader slices it"
                           % (section[0], section[1]))
    lines = [" ".join(x.split()) for x in whole[start:end].split("\n")]
    rows, last = {}, None
    for line in [x for x in lines if x]:
        m = DOC_ROW.match(line)
        if m:
            d = int(m.group(1))
            member, role = clean(DOC_LEADER_TAIL.sub("", m.group(2)))
            if not is_name(member):
                last = None
                continue
            rows[d] = {"name": member, "vacant": False, "role": role,
                       "phone": m.group(3).strip()}
            last = d
            continue
        em = DOC_EMAIL.match(line)
        # the address sits on the row BELOW its member and nowhere else, so it
        # is only ever attached to the row just read — never searched for
        if em and last is not None:
            rows[last]["email"] = em.group(1)
            last = None
    return rows


def witness_profiles(page_html, prefix):
    """District -> (name, profile url) read one supervisor block at a time."""
    out = {}
    for inner in DOC_BLOCK.findall(page_html):
        links = set(DOC_PROFILE.findall(inner))
        if len(links) != 1:
            continue
        text = " ".join(html_lib.unescape(_TAG.sub(" ", inner)).split())
        m = DOC_DISTNAME.match(text)
        if not m:
            continue
        d = int(m.group(1))
        if d in out:            # two blocks claim one district: trust neither
            out[d] = None
            continue
        out[d] = (clean(m.group(2))[0], prefix + links.pop())
    return {d: v for d, v in out.items() if v}


def scrape_witnessed_document(spec):
    """A roster read from a county DOCUMENT and witnessed against its page."""
    pdf_bytes, edition = fetch_bytes(spec["document"], timeout=90)
    print("  doc  %-12s edition %s (%d KB)"
          % (spec["name"], edition, len(pdf_bytes) // 1024), file=sys.stderr)
    rows = document_rows(pdf_bytes, spec["section"])
    seats = spec["seats"]
    want = set(range(1, seats + 1))
    if set(rows) != want:
        raise RuntimeError("%s: the directory resolved %d of %d districts "
                           "(missing %s) — re-read the document"
                           % (spec["name"], len(rows), seats,
                              sorted(want - set(rows))))

    page = fetch(spec["witness"])
    lines = to_lines(page)
    witness = _windowed(lines, WINDOW_AFTER)
    if set(witness) != want:
        raise RuntimeError("%s: the witness page resolved %d of %d districts "
                           "(missing %s) — the two surfaces can no longer check "
                           "each other, so neither ships"
                           % (spec["name"], len(witness), seats,
                              sorted(want - set(witness))))
    differ = [(d, rows[d]["name"], witness[d][0]) for d in sorted(want)
              if rows[d]["name"] != witness[d][0]]
    if differ:
        raise RuntimeError(
            "%s: the directory and the board page name different supervisors "
            "(%s) — one of the two is stale and this scraper cannot tell which"
            % (spec["name"], "; ".join("D%d %r vs %r" % x for x in differ)))

    # roles: shipped only where the page's own leadership sentence agrees.
    # Exactly one row may be marked chair and one vice-chair; anything else is
    # the document saying something this reader does not understand.
    def marked_as(vice):
        who = [v["name"] for v in rows.values() if v.get("role")
               and bool(re.match(r"(?i)vice", v["role"])) == vice]
        return who[0] if len(who) == 1 else None

    doc_chair, doc_vice = marked_as(False), marked_as(True)
    stated = LEADERSHIP.search(" ".join(lines))
    if not stated:
        print("  note %-12s the board page no longer states its leadership in a "
              "sentence this reader parses — roles withheld" % spec["name"],
              file=sys.stderr)
        confirmed = False
    else:
        chair, vice = clean(stated.group(1))[0], clean(stated.group(2))[0]
        confirmed = (doc_chair is not None and doc_vice is not None
                     and chair == doc_chair and vice == doc_vice)
        if not confirmed:
            print("  note %-12s the board page states chair %r / vice-chair %r "
                  "where the directory marks %r / %r — roles withheld"
                  % (spec["name"], chair, vice, doc_chair, doc_vice),
                  file=sys.stderr)
    if confirmed:
        print("  role %-12s chair %s, vice-chair %s (both witnessed on the "
              "county's own board page)" % (spec["name"], doc_chair, doc_vice),
              file=sys.stderr)
    else:
        for row in rows.values():
            row["role"] = None

    profiles = witness_profiles(page, spec["profile_prefix"])
    linked = 0
    for d, row in rows.items():
        found = profiles.get(d)
        # paired on the NAME the block itself carries, so a block that has
        # shifted takes its own link with it rather than someone else's
        if found and found[0] == row["name"]:
            row["url"] = found[1]
            linked += 1
    print("  link %-12s %d of %d supervisors carry the county's own profile page"
          % (spec["name"], linked, seats), file=sys.stderr)
    return {str(d): rows[d] for d in sorted(rows)}

# --- officers published ABOVE the district list ------------------------------
# Juneau and Oneida name their chair and vice-chairs in a block of their own,
# separate from the district rows, so the roles never reach a member through
# `split_role` (which only sees a role attached to the name it is reading).
# That is not cosmetic: the county card's board chair is reconciled weekly
# against this roster, and a roster with NO marked chair makes the builder
# WITHHOLD the Blue Book's chair rather than supersede it — which is how
# Juneau's card lost a chair its own page names in plain text.
#
# THE JOIN IS ON A FULL NAME AND MUST BE UNIQUE, and every join PRINTS. A role
# guessed onto the wrong supervisor is worse than no role at all.
#
# A COUNTY MAY PUBLISH ITS OFFICERS ON A DIFFERENT PAGE FROM ITS DISTRICT LIST.
# Sheboygan's roster table names 25 supervisors and no officer at all; its
# County Board landing page — the roster page's own parent — prints
# "Keith Abler / Chairperson / Curt Brauer / Vice Chairperson". So the officer
# scan takes its OWN page here, fetched separately, while the districts still
# come from the roster page. `reading` pins the direction the same way every
# roster reading in this file is pinned, and for the same reason: see
# `attach_officer_roles`. It is the SAME field Rock pins in OFFICER_NAME_SIDE,
# under that field's name: Sheboygan arrived calling it "above"/"below" and Rock
# "before"/"after", and two names for one mechanism is how a reader comes to
# believe there are two.
OFFICER_PAGES = {
    "55117": {"url": "https://www.sheboygancounty.com/departments/county-board/",
              "name_side": "before"},
}

OFFICER_LINE = re.compile(r"^\s*(%s)\s*(?:[-–—:]\s*(.+))?$" % _ROLE, re.I)
# Monroe heads its two officers "County Board Chair" and "County Board
# Vice-Chair", which `_ROLE` (County? + ordinal? + Vice? + Chair) cannot match,
# so it gets a heading pattern one word wider — PINNED TO ITSELF, the way every
# reading direction in this file is pinned, and for a reason that was measured
# rather than assumed. Run fleet-wide it moved three counties, and one of them
# moved WRONG: Dunn's page ends with a welcome letter to new supervisors,
# signed "Kelly McCullough / County Board Chairman", while the county's own
# roster on the same page marks "Chair - Randy L. Prochnow" at district 24. The
# wider pattern read the SIGNATURE as the county's statement of who chairs the
# board, which would have marked two chairs in one county and stopped the
# officer builder outright. A SIGNATURE IS NOT A ROSTER, and a role guessed
# onto the wrong supervisor is worse than no role at all — so the widening
# reaches exactly the county whose officer block was read.
OFFICER_LINE_BOARD = re.compile(
    r"^\s*((?:County\s+)?(?:Board\s+)?(?:(?:1st|2nd|First|Second)\s+)?"
    r"(?:Vice[\s\-]?)?Chair(?:man|person|woman)?)\s*(?:[-–—:]\s*(.+))?$", re.I)
OFFICER_LINE_BY_COUNTY = {"55081": OFFICER_LINE_BOARD}      # Monroe
# str.title() turns "1st Vice Chair" into "1St Vice Chair" — it upper-cases the
# letter after every digit. Ordinals keep their own casing.
_ORDINAL = re.compile(r"^\d+(?:st|nd|rd|th)$", re.I)
# Only a COLON. A leading dash also joins two lines on some pages, but it is
# equally the bullet of an unrelated row ("- District 5"), and a separator that
# can mean either is not evidence of anything.
SPLIT_OFFICER = re.compile(r"^\s*:\s*")


def attach_officer_roles(lines, districts, county, name_side=None,
                         officer_line=OFFICER_LINE, source_url=None):
    """Give a member the role their county states in its officers block.

    `source_url` is set only where the role came off a DIFFERENT page from the
    district list, and lands on the row as `role_url`.

    `name_side` pins which neighbour of a bare role line carries its name, for
    the counties that print officers as a run of consecutive name/role pairs —
    where both neighbours read as names and the ambiguous case below would
    otherwise attach nothing. Pinned per county in OFFICER_NAME_SIDE, never
    detected, for the same reason the district readings are.

    `officer_line` is the heading pattern, widened per county where a county
    words its own officer headings past what `OFFICER_LINE` matches — pinned in
    OFFICER_LINE_BY_COUNTY, and to that county alone, so no other county's
    reading moves.
    """
    by_name = {}
    for d, row in districts.items():
        if row.get("name"):
            by_name.setdefault(row["name"], []).append(d)
    for i, line in enumerate(lines):
        m = officer_line.match(line)
        if not m:
            continue
        role = role_case(m.group(1))
        # THE SAME BEFORE/AFTER AMBIGUITY THE WHOLE FILE PINS, one block over,
        # and it is not hypothetical: a first draft scanned FORWARD only and
        # filed Jefferson's Blane Poulson — its Second Vice Chair — as First,
        # because Jefferson prints the NAME above the role ("James Braughler /
        # First Vice Chair / phone") where Brown prints it below ("Chair /
        # Buckley, Patrick"). Three cases, and only the first two attach:
        #   * the role line carries its own name  -> use it, and never look
        #     further; Juneau lists three officers in consecutive lines, so a
        #     fall-through files each role under the NEXT officer's name;
        #   * the county pins a side (OFFICER_NAME_SIDE) -> that neighbour, and
        #     only that one; Rock's three officers are consecutive name/role
        #     pairs, so every role line has a name on both sides and the
        #     ambiguous case below would attach none of them;
        #   * exactly ONE neighbouring line reads as a name -> that one;
        #   * BOTH neighbours read as names -> ambiguous, attach nothing.
        before = lines[i - 1] if i > 0 else ""
        after = lines[i + 1] if i + 1 < len(lines) else ""
        if m.group(2):
            cands = [m.group(2)]
        elif name_side:
            pinned = before if name_side == "before" else after
            cands = [pinned] if is_name(pinned) else []
        elif SPLIT_OFFICER.match(lines[i + 1] if i + 1 < len(lines) else ""):
            # "Role: Name" written as one line by the county and cut in two by
            # the markup: Outagamie's block is <strong>Vice-Chairperson</strong>
            # ": Rick Lautenschlager", and `to_lines` breaks on </strong>. The
            # COLON is what makes this unambiguous — it is the tail of the
            # county's own sentence, not a neighbouring row — so this case is
            # taken before the two-neighbour scan below, which would read the
            # block's consecutive officers as ambiguous and attach nothing.
            cands = [SPLIT_OFFICER.sub("", lines[i + 1], count=1)]
        else:
            b_ok, a_ok = is_name(before), is_name(after)
            if b_ok and a_ok:
                print("  note %-12s role %r sits between two names (%r, %r) — "
                      "not attached" % (county, role, before, after), file=sys.stderr)
                continue
            cands = [after] if a_ok else ([before] if b_ok else [])
        for cand in cands:
            if not cand:
                continue
            who = clean(cand)[0]
            hits = by_name.get(who)
            if not hits:
                continue
            if len(hits) > 1:
                print("  note %-12s %r holds %d districts — role %r not attached"
                      % (county, who, len(hits), role), file=sys.stderr)
                break
            d = hits[0]
            if districts[d].get("role"):
                break                       # the row already said so
            districts[d]["role"] = role
            if source_url:
                # the role came off a DIFFERENT page from the district list, so
                # the row records where — the officer builder links a
                # superseded chair to where the county states it, and
                # Sheboygan's roster table states no officer at all
                districts[d]["role_url"] = source_url
            print("  role %-12s district %s: %s -> %s"
                  % (county, d, who, role), file=sys.stderr)
            break
    return districts


# COUNTIES WHOSE ONE VACANCY CARRIES NO DISTRICT NUMBER. Marinette lists its
# board alphabetically by surname, every row "Name - District N" except one
# that reads only "VACANT SEAT" with the ward description beneath it. Twenty-
# nine districts are named, one is not, and the county states one empty seat.
#
# ASSIGNING THAT SEAT IS AN INFERENCE, and it is opt-in per county rather than
# a general rule because a page that drops a numbered row for any OTHER reason
# would otherwise get a silently invented vacancy. The gate is arithmetic and
# is checked on every run: EXACTLY ONE district unclaimed AND EXACTLY ONE
# vacancy line that carries no district number. If the page ever names two
# vacancies, or loses a second row, the county fails its count guard as before
# and nothing is inferred.
ELIMINATION_VACANCY = {"55075"}      # Marinette

# COUNTIES THAT PUBLISH A PAGE PER SUPERVISOR. Sheboygan's roster table links
# each name to its own district page, and that page — not the table — carries
# the county e-mail and the contact phone. Twenty-five extra fetches a week buy
# 24 official e-mail addresses on a file that carried 56 in total before them,
# so the trade is worth making; nothing else in this table needs it.
#
# THE ADDRESS ON THOSE PAGES IS NOT CARRIED, and that is the same rule Taylor's
# document roster states: the "Contact Information" block leads with the
# supervisor's HOME ("W6259 Hammann Road", "N185 County Road DE"), and a
# supervisor's house is not an office location. The published contact phone and
# the county e-mail are official contact details and do ship.
#
# THE PAGE IS A WITNESS BEFORE IT IS A SOURCE. A district page is used only if
# its own heading names the person the table filed under that district — a
# fold on first name + surname, because the two surfaces style the same person
# apart (the table's "Thomas G. Wegner" is the page's "Thomas Wegner"). The
# NAME always comes from the table; the page only ever adds contact.
#
# THE FLOORS DETECT A RESHAPE, NOT AN EDIT. A supervisor genuinely without a
# published e-mail moves these by one (district 3 has none today); a page
# template changing moves all 25 at once. Below a floor the county fails its
# run rather than shipping a thin contact set, because the roster retention
# gate CANNOT catch this one: county-board-members.json has more than 200
# top-level keys, so that gate measures it file-level, and Sheboygan's 24
# e-mails vanishing reads there as 80 -> 56 — a 30% dip that passes every
# threshold it has. A guard has to live where the field does.
MEMBER_PAGES = {
    "55117": {
        "url": "https://www.sheboygancounty.com/departments/county-board/"
               "county-board-supervisors/district-%d",
        # only the COUNTY's own domain: a supervisor's page can carry a
        # personal or employer address too, and that is not an office contact
        "email_domain": "@sheboygancounty.com",
        # measured 2026-08-29: 25 witnessed, 24 e-mails, 25 phones
        "floors": {"witness": 23, "email": 20, "phone": 22},
    },
}
_MAILTO = re.compile(r"(?i)mailto:([^\"'?<>\s]+)")
_PHONE = re.compile(r"Phone:\s*(\(?\d{3}\)?[\s.-]*\d{3}[-.\s]?\d{4})")
# The heading is "<Name> - District <n>"; anchored on the district number so a
# page that lists several people can only ever answer for its own district.
_MEMBER_HEADING = "(?:^|[>\\s])([A-Z][^|<>\\n]{2,42}?)\\s*[-\u2013\u2014]\\s*District\\s+%d\\b"


def member_pages(spec, districts, county):
    """Add the contact each supervisor's OWN page publishes, witnessed by it."""
    got = {"witness": 0, "email": 0, "phone": 0}
    for key, row in sorted(districts.items(), key=lambda kv: int(kv[0])):
        if row.get("vacant") or not row.get("name"):
            continue
        url = spec["url"] % int(key)
        try:
            page = fetch(url)
        except Exception as e:      # noqa: BLE001 - one page never fails the county
            print("  note %-12s district %s page unfetched (%s)"
                  % (county, key, e), file=sys.stderr)
            continue
        flat = " ".join(html_lib.unescape(_TAG.sub(" ", page)).split())
        m = re.search(_MEMBER_HEADING % int(key), flat)
        if not m or _fold_person(m.group(1)) != _fold_person(row["name"]):
            print("  note %-12s district %s page names %r, the table names %r "
                  "— no contact taken"
                  % (county, key, (m.group(1).strip() if m else None), row["name"]),
                  file=sys.stderr)
            continue
        got["witness"] += 1
        row["url"] = url
        domain = spec["email_domain"].lower()
        mail = [a for a in _MAILTO.findall(html_lib.unescape(page))
                if a.lower().endswith(domain)]
        if mail:
            row["email"] = mail[0]
            got["email"] += 1
        phone = _PHONE.search(flat)
        if phone:
            row["phone"] = " ".join(phone.group(1).split())
            got["phone"] += 1
        time.sleep(0.3)
    print("  pages %-12s %d witnessed, %d e-mails, %d phones of %d seats"
          % (county, got["witness"], got["email"], got["phone"], len(districts)),
          file=sys.stderr)
    short = {k: (got[k], v) for k, v in spec["floors"].items() if got[k] < v}
    if short:
        raise RuntimeError(
            "%s: the per-supervisor pages resolved %s against the pinned floors "
            "— the page template has changed shape; re-read one before shipping"
            % (county, ", ".join("%s %d (floor %d)" % (k, a, b)
                                 for k, (a, b) in sorted(short.items()))))
    return districts


def eliminated_vacancy(lines, seats, found, vacant, county):
    """The single unclaimed district, when the page states a single unnumbered
    vacancy. Returns the district number, or None when the arithmetic does not
    force it."""
    unclaimed = [d for d in range(1, seats + 1) if d not in found and d not in vacant]
    if len(unclaimed) != 1:
        return None
    loose = [l for l in lines if VACANT.search(l) and not DIST.search(l)]
    if len(loose) != 1:
        print("  note %-12s %d unnumbered vacancy line(s) for %d unclaimed district(s)"
              " — nothing inferred" % (county, len(loose), len(unclaimed)), file=sys.stderr)
        return None
    print("  infer %-12s district %d is the county's one unnumbered %r row "
          "(29 of 30 numbered, one vacancy stated)"
          % (county, unclaimed[0], loose[0].strip()), file=sys.stderr)
    return unclaimed[0]


# --- what a fielded county is held to ----------------------------------------
# THREE WITNESSES, none of them the page checking itself.
#
# ONE, THE E-MAIL ON EVERY SEAT'S OWN ROW. Sauk prints a county mailbox beside
# each supervisor, and the county builds it as first.last@saukcountywi.gov —
# so a reading shifted by one would file a name under a district whose e-mail
# names somebody else, on all thirty rows at once. That is the shift this whole
# file pins reading directions to avoid, answered here per seat rather than by
# a pin. Twenty-nine of thirty agree exactly; the thirtieth is `name_fixes`.
#
# TWO, THE WARD COMPOSITION AGAINST LTSB. Each panel lists the wards the
# district is built from, and LTSB's statewide ward layer — the same service
# the app's Municipal Ward layer draws — carries a SUPERID on every ward. That
# makes the county's numbering checkable against the state's, which is what the
# roster's district key actually rests on: the map is LTSB's and the people are
# the county's, and nothing else in this file proves the two number their
# districts alike. Measured 2026-08-29: 117 of the county's 118 listed wards
# land in LTSB's same-numbered district, and BOTH one-district shifts land
# ZERO — the witness discriminates completely.
#
# THREE, THE CLERK'S OWN CANDIDATE FILING LIST for the 2026-2028 term, which
# is where `name_fixes` and `phone_owner` come from. It is a January snapshot
# of who FILED and is never used as a roster (it has District 1 as Jake Roxen,
# where the county's maintained directory names Wally Czuprynko), but it is an
# independent county document for a name and a phone number.
#
# NO ROLE IS ATTACHED, AND THAT IS DELIBERATE. This page marks no chair, and
# `attach_officer_roles` therefore has nothing to find — Sauk names its chair
# on a DIFFERENT page (co.sauk.wi.us/countyboard/county-board-contacts, "Tim
# McCumber County Board Chair"), and a role read off one page cannot honestly
# be sourced to another, since the roster carries one sourceUrl per county.
# Nothing is lost: the officer builder's chair reconciliation finds the Blue
# Book's "Tim McCumber" sitting in district 20 and CONFIRMS the dated book row
# rather than withholding it, and the county's own contacts page independently
# agrees with the book on both the name and the phone number district 20
# carries here.
LTSB_WARD_QUERY = ("https://services1.arcgis.com/FDsAtKBk8Hy4cAH0/arcgis/rest/"
                   "services/WI_Municipal_Wards_Current/FeatureServer/0/query")

FIELDED_PINS = {
    "55111": {
        # ONE SEAT'S NAME AND E-MAIL DISAGREE. District 4 prints "Schroder,
        # Palmer" beside palmer.schroeder@saukcountywi.gov, and the Clerk's
        # candidate filing list for this very term prints "Palmer B.
        # Schroeder" — two county documents to one, so the surname the county
        # mails to is what ships. The pin asserts the page still prints the
        # misspelling: the day Sauk fixes its own record, this FAILS and the
        # entry is deleted rather than quietly correcting a name forever.
        "name_fixes": {4: ("Palmer Schroder", "Palmer Schroeder")},
        # A PHONE PUBLISHED FOR TWO PEOPLE IS NOT A PER-PERSON PHONE. Districts
        # 28 (Tatone) and 29 (Evert) both carry 608-963-4067; the Clerk's
        # filing list gives that number as Evert's and Tatone's as another, so
        # the directory has copied one supervisor's number onto a second seat.
        # Evert keeps it on two documents' agreement and Tatone's is WITHHELD —
        # the number this project holds for her is demonstrably his, and a
        # candidate's own January phone is not the county's answer to "how do
        # I reach my supervisor". Any duplicate NOT pinned here loses the
        # number on every seat that shares it, which is the safe direction.
        "phone_owner": {"6089634067": 29},
    },
}


def digits(text):
    return re.sub(r"[^0-9]", "", str(text or ""))


def _email_agrees(name, email):
    """first.last@ against the name on the same row — the anti-shift witness."""
    local = str(email or "").split("@")[0].lower()
    parts = [re.sub(r"[^a-z]", "", x) for x in local.split(".")]
    parts = [x for x in parts if x]
    toks = [re.sub(r"[^a-z]", "", t) for t in str(name or "").lower().split()]
    toks = [t for t in toks if t]
    if len(parts) < 2 or len(toks) < 2:
        return False
    return parts[0] == toks[0] and parts[-1] == toks[-1]


# --- Jackson: a district-keyed roster PDF the county links from its own page ---
#
# THE COUNTY'S OWN SITE DOES NOT NAME A SUPERVISOR ANYWHERE IN ITS HTML, which
# is why Jackson sat in the gap block and why a reader looking for a board page
# comes away empty. co.jackson.wi.us links "County Board Supervisor Listing"
# from its home nav, that page carries no roster either, and what it holds is a
# LINK to `2026_-_2027_County_Board_Members.pdf` — a four-page document with a
# full text layer naming all 19 districts, each with its ward composition, the
# supervisor, a phone and a county e-mail. A PDF IS A FORMAT, NOT A BLOCKER
# (the Adams rule); the disqualifier was always "no district column", and this
# document is nothing but district columns.
#
# THE DOCUMENT URL IS DISCOVERED, NEVER PINNED. Its filename carries the term
# ("2026_-_2027"), so the next board's document is at a different address and a
# pinned URL would go on serving the previous term's names for two years — the
# exact staleness this project keeps finding on other people's pages. The link
# is found on the listing page each run and its resolved address is recorded, so
# the run log names the edition that answered.
#
# THIS IS NOT THE ADAMS ROUTE AND DOES NOT REUSE IT. Adams's directory is a
# Google Drive file whose names sit ON the contact line and are witnessed by a
# `districtN@` mailbox; Jackson's document is on the county's own host, prints
# the name on its own line, and gives every supervisor a personal
# `First.Last@` address — so there is no per-district mailbox to check the
# heading against, and the parser walks blocks rather than contact lines.
#
# FOUR TRAPS, ALL MEASURED 2026-08-31:
#   1. TWO DASH FORMS. Four headings use a hyphen and fifteen an EN DASH, and
#      one of those has no space after it ("DISTRICT 12 -KNAPP"). A heading
#      regex that pins one dash silently loses three-quarters of the board.
#   2. HEADINGS WRAP. Districts 3, 7, 9 and 12 run their ward composition onto
#      a second line, so "the line after the heading" is ward text and NOT the
#      supervisor — district 9's is the bare number "562". The name is the
#      first line in the block that reads as a name and is not an ALL-CAPS ward
#      run; every address line carries digits and `is_name` refuses it anyway.
#   3. ONE PHONE HAS NO LABEL. Eighteen print "Phone 715-...", district 15
#      prints the number bare. Anchoring on the county's own "Phone" label —
#      which is what Calumet needed — would drop exactly one number here, and
#      the seat count would not notice. PDF_PHONE matches the number itself.
#   4. THE E-MAIL IS NOT DERIVABLE FROM THE NAME. District 18 is "Jerry
#      Schmidt" at `Jerrold.Schmidt@`, district 19 "Ed Chamberlain" at
#      `Edward.Chamberlain@`. Both are shipped exactly as the county publishes
#      them; neither is "corrected" toward the other, because a display name and
#      a mailbox are two different facts about one person.
#
# THE HOME ADDRESSES ARE NOT CARRIED, as everywhere in this fleet — every block
# prints the supervisor's house, and the phone and county e-mail beside it are
# the official contact details that do ship.
#
# THE WITNESS IS THE COUNTY'S OWN WARD COMPOSITION AGAINST LTSB'S FILING, and
# it is worth more here than the name checks are. The document says District 1
# is Garfield ward 1 plus Cleveland; LTSB's statewide ward layer independently
# assigns those wards to Jackson district 1. All 50 listed wards land in their
# same-numbered LTSB district and a one-district shift matches ZERO, so the two
# publishers describe one plan and one numbering.
#
# IT MATCHES WITHOUT THE CITY/TOWN/VILLAGE CODE ON PURPOSE, unlike
# `_ward_witness`. The document does not state the code reliably — "BLACK RIVER
# FALLS" is a CITY written bare while "CITY POINT" is a TOWN whose name merely
# begins with the word — so deriving one would be inference, and a wrong
# derivation would fail a correct roster. Dropping it collides exactly one pair
# (the Town and Village of Melrose, both in district 6), which cannot hide a
# shift: a shift moves whole districts, not one ward.
JK_HEAD = re.compile(r"^\s*DISTRICT\s+(\d{1,2})\s*[-–—]\s*(.*)$")
JK_MAIL = re.compile(r"\b([A-Za-z][A-Za-z.'-]*)@jacksoncountywi\.gov\b", re.I)
JK_DOMAIN = "jacksoncountywi.gov"
# an ALL-CAPS ward run, a bare population, or a fragment of either
JK_WARDLINE = re.compile(r"^[A-Z0-9][A-Z0-9 ,.&'#–-]*$")
# "GARFIELD W1 574", "VILLAGE OF ALMA CENTER 487", "ALMA W1, W3 & W5 548" —
# a municipality, an optional ward list, then the population that ends the entry
JK_WARD_ENTRY = re.compile(r"([A-Za-z][A-Za-z .']*?)\s*"
                           r"((?:W\d+(?:\s*[,&]\s*W?\d+)*)?)\s*(\d{2,5})\b")
JK_MIN_EMAILS = 17       # 19 of 19 publish one today
JK_MIN_PHONES = 17       # 19 of 19 today; the floor tolerates two dropping out


def _jk_norm(text):
    return re.sub(r"[^a-z]", "", text.lower())


def _jk_wards(text):
    """{(municipality, ward number)} from a district's composition text."""
    out = set()
    for m in JK_WARD_ENTRY.finditer(text):
        name = re.sub(r"(?i)^\s*(?:village|city|town)\s+of\s+", "", m.group(1)).strip(" ,&")
        if not name:
            continue
        wards = [int(x) for x in re.findall(r"\d+", m.group(2))] or [1]
        for w in wards:
            out.add((_jk_norm(name), w))
    return out


def ward_number_witness(fips, county, wards, seats, min_pairs=None, munis=None):
    """The county's own composition against LTSB's ward-level SUPERID.

    SHARED, NOT JACKSON'S. It was written for Jackson and is the strongest
    check this file has, because it tests the one thing a roster cannot check
    about itself: that the county's district NUMBERS mean what the shipped
    geometry's numbers mean. Clark calls it too — its Clerk prints each
    district's municipalities and wards beside the number, so the same
    comparison runs on a completely different document shape.

    A FETCH FAILURE IS NOT A DISAGREEMENT — an unreachable witness says nothing
    about the roster, so it stands aside; a witness that RUNS and disagrees
    fails the county, because then the district KEY is what is in doubt.
    """
    try:
        data = _fetch_json(
            LTSB_WARD_QUERY + "?where=CNTY_FIPS%%3D%%27%s%%27&outFields="
            "MCD_NAME,CTV,WARDID,SUPERID&returnGeometry=false&f=json" % fips)
        feats = data.get("features") or []
        if not feats:
            raise RuntimeError("no wards returned")
    except Exception as e:      # noqa: BLE001 - the witness, never the source
        print("  WITNESS SKIPPED %-9s LTSB ward layer unreachable (%s) — the "
              "roster ships unwitnessed this run" % (county, e), file=sys.stderr)
        return
    ltsb, types_by_name = {}, {}
    for f in feats:
        a = f.get("attributes") or {}
        ctv, name = str(a.get("CTV", "")).lower()[:1], _jk_norm(str(a.get("MCD_NAME", "")))
        ltsb.setdefault(int(a["SUPERID"]), set()).add(
            (ctv, name, int(str(a.get("WARDID") or 0))))
        types_by_name.setdefault(name, set()).add(ctv)

    # THE TYPE IS LOAD-BEARING ONLY WHERE THE NAME IS AMBIGUOUS. Marathon has
    # five names that are two municipalities at once (Elderon, Mosinee, Spencer,
    # Wausau, Weston) and Pierce three, and for those the county's town/village
    # word is the only thing separating them — a mismatch there is a real
    # disagreement. Where LTSB files a name under exactly ONE type in that
    # county, the word carries no information and a mismatch is a stale LABEL:
    # Marathon's District 37 says "Town of Rib Mountain" where its own District
    # 36 says "Village", the state says Village, and both agree on wards
    # 1,2,7,8,9 versus 3,4,5,6,10. Refusing a county over the word while its
    # numbers agree exactly would be refusing the wrong thing. Relabelled pairs
    # are counted and printed, never silently absorbed.
    relabelled = set()
    # A TYPE OF None MEANS THE DOCUMENT NEVER SAID, which is a different thing
    # from saying it wrong and is not a relabelling. Forest writes its towns
    # bare — "Argonne, Ward 1, Hiles, Lincoln, Ward 1" — and spells out only
    # the one name that is two municipalities in that county ("Town of
    # Crandon", "City of Crandon"). So the COUNTY names the municipality and
    # LTSB SUPPLIES THE TYPE, which is a resolution rather than an assumption:
    # a bare name LTSB files under two types stays None, matches nothing, and
    # falls out as a stray, so the witness FAILS rather than picking one.
    # Assuming "bare means town" would have been right in Forest and is
    # exactly the guess this returns a measurement instead of.
    supplied = set()

    def settle(key):
        """The county's (type, name[, ward]) with the type corrected or supplied."""
        filed = types_by_name.get(key[1])
        if filed and len(filed) == 1 and key[0] not in filed:
            (supplied if key[0] is None else relabelled).add(
                (key[0], key[1], next(iter(filed))))
            return (next(iter(filed)),) + key[1:]
        return key

    wards = {d: {settle(k) for k in v} for d, v in wards.items()}
    if munis:
        munis = {d: {settle(k) for k in v} for d, v in munis.items()}
    listed = sum(len(v) for v in wards.values())
    # THE FLOOR IS PER DOCUMENT, NOT PER COUNTY BOARD. Jackson names every ward
    # of every municipality, so twice the seat count is a fair bar there. Clark
    # names some municipalities WHOLE ("Town of Withee", "Village of Curtiss"),
    # which is a complete statement of that district's composition carrying no
    # ward number at all — 56 numbered pairs across 29 seats is its healthy
    # state, not a document that has stopped printing compositions. Expanding a
    # whole-municipality mention from LTSB's own file would make the witness
    # score data it supplied itself, so the floor moves and the prose does not.
    floor = 2 * seats if min_pairs is None else min_pairs
    if listed < floor:
        raise RuntimeError("%s: the document lists only %d ward pairs across %d "
                           "districts (floor %d) — it has stopped printing its "
                           "ward composition, and the numbering witness with it"
                           % (county, listed, seats, floor))
    hit = sum(len(v & ltsb.get(d, set())) for d, v in wards.items())
    shifts = [sum(len(v & ltsb.get(d + off, set())) for d, v in wards.items())
              for off in (1, -1)]
    print("  witness %-12s %d/%d listed wards in LTSB's own district (shifts %d/%d)"
          % (county, hit, listed, shifts[0], shifts[1]), file=sys.stderr)
    if supplied:
        print("  note    %-12s %d municipality name(s) carry no town/village/city "
              "word in the document; LTSB files each under exactly one type here, "
              "so the type comes from the state's own filing: %s"
              % (county, len(supplied),
                 ", ".join("%s (%s)" % (n, t)
                           for _, n, t in sorted(supplied, key=lambda k: k[1]))[:200]),
              file=sys.stderr)
    if relabelled:
        for was, name, now in sorted(relabelled):
            print("  note    %-12s the document calls %s a '%s' and LTSB files it as "
                  "a '%s'; that name is only one municipality here, so the wards "
                  "decide" % (county, name, was, now), file=sys.stderr)
    # SORT KEY, NOT THE TUPLE: a type can be None here (see settle() above), and
    # an UNRESOLVED one is precisely the case this note has to survive to print
    # — sorting None against 't' raises TypeError and would crash the failure
    # path instead of reporting it.
    def _order(k):
        return (str(k[0]),) + tuple(str(x) for x in k[1:])

    stray = sorted((k for d, v in wards.items() for k in v - ltsb.get(d, set())),
                   key=_order)
    if stray:
        print("  note    %-12s %d listed ward(s) are not in LTSB's same-numbered "
              "district: %s" % (county, len(stray),
                                ", ".join("%s %s w%d in D%d" % (k[0], k[1], k[2], d)
                                          for d, v in sorted(wards.items())
                                          for k in sorted(v - ltsb.get(d, set()),
                                                          key=_order))[:220]),
              file=sys.stderr)
    # THE SHIFT TEST IS COMPARATIVE, NOT ABSOLUTE. It asks whether the county's
    # numbering fits LTSB's file BETTER at its own offset than one district
    # along, which is the shape a renumbering takes. It was written as "any
    # shifted match at all fails", which is true of Jackson's document and false
    # in general: Clark scores a perfect 56/56 at its own offset and still picks
    # up 1 and 2 stray hits shifted, because two neighbouring districts happen
    # to contain a like-numbered ward in different municipalities. Refusing a
    # county on 2 coincidences against 56 exact matches would reject a roster
    # that agrees with the state completely. A real renumbering inverts the
    # ratio — the shift scores near everything and the true offset near nothing.
    if hit and max(shifts) > 0.5 * hit:
        raise RuntimeError("%s: %d of its listed wards land in LTSB's "
                           "same-numbered district but %d land one district off "
                           "— too close to call, and the two publishers may have "
                           "renumbered apart; re-read both before shipping"
                           % (county, hit, max(shifts)))
    if not hit and any(shifts):
        raise RuntimeError("%s: NONE of its listed wards land in LTSB's "
                           "same-numbered district and %d land one off — the "
                           "document is numbered against a different plan"
                           % (county, max(shifts)))
    # A WARD LTSB DOES NOT HAVE AT ALL IS NOT EVIDENCE ABOUT THE NUMBERING, and
    # conflating the two cases is what this separates. There are two ways a
    # listed pair can miss: the ward EXISTS in LTSB's filing under a different
    # district — a real disagreement about which seat that ground belongs to,
    # the thing this witness is for — or the ward is ABSENT from the county's
    # ward fabric entirely, which says the two publishers disagree about what
    # wards exist and says nothing whatever about district numbers. Sawyer is
    # the case: its Supervisory Districts page names City of Hayward ward 6 and
    # Town of Hayward ward 8, and LTSB's filing runs the city to ward 5 and the
    # town to ward 7. Every ward the two publishers BOTH name agrees on its
    # district. Counting those two as numbering disagreements refused a county
    # whose numbering agrees completely.
    #
    # THE ABSENT ONES ARE STILL BOUNDED AND STILL PRINTED. A page naming a few
    # wards the state has since consolidated is an ordinary stale paragraph; a
    # page where a third of the wards do not exist is a page describing a
    # different decade, and that is a reason to stop rather than to ship.
    exists = {k for v in ltsb.values() for k in v}
    absent = sorted((k for d, v in wards.items() for k in v - ltsb.get(d, set())
                     if k not in exists), key=_order)
    comparable = listed - len(absent)
    # AND A WARD MISSING FROM *THIS COUNTY'S* SLICE MAY SIT IN THE NEXT COUNTY'S.
    # The query above is per CNTY_FIPS, so a municipality that CROSSES a county
    # line has its other wards filed under the neighbour. Marathon is the case:
    # its composition names City of Marshfield wards 1, 2 and 3, LTSB files
    # Marathon's Marshfield as wards 12, 16 and 19, and 1-3 are there under WOOD
    # County — the city straddles the line. Calling those "absent from LTSB" is
    # simply wrong, and a wrong explanation printed weekly is how the next
    # reader is misled. Sawyer's two are the other kind: City of Hayward runs to
    # ward 5 and Town of Hayward to ward 7 in the only county either sits in.
    # One extra request, and only when there is something to explain.
    crossing = set()
    if absent:
        try:
            names = sorted({k[1] for k in absent})
            where = " OR ".join("MCD_NAME='%s'" % n for n in
                                sorted({str(a.get("attributes", {}).get("MCD_NAME"))
                                        for a in feats
                                        if _jk_norm(str(a.get("attributes", {})
                                                        .get("MCD_NAME", ""))) in names}))
            if where:
                other = _fetch_json(
                    LTSB_WARD_QUERY + "?where=%s&outFields=MCD_NAME,CTV,WARDID,"
                    "CNTY_FIPS&returnGeometry=false&f=json"
                    % urllib.parse.quote(where))
                for f in other.get("features") or []:
                    a = f.get("attributes") or {}
                    if str(a.get("CNTY_FIPS")) == fips:
                        continue
                    crossing.add((str(a.get("CTV", "")).lower()[:1],
                                  _jk_norm(str(a.get("MCD_NAME", ""))),
                                  int(str(a.get("WARDID") or 0))))
        except Exception as e:      # noqa: BLE001 - the explanation, never the source
            print("  note    %-12s could not check whether the unmatched wards sit "
                  "in a neighbouring county (%s)" % (county, e), file=sys.stderr)
    across = [k for k in absent if k in crossing]
    nowhere = [k for k in absent if k not in crossing]
    if across:
        print("  note    %-12s %d listed ward(s) are filed under a NEIGHBOURING "
              "county, because that municipality crosses the county line (%s) — "
              "not a numbering disagreement"
              % (county, len(across),
                 ", ".join("%s %s w%d" % k for k in across)[:180]), file=sys.stderr)
    if nowhere:
        print("  note    %-12s %d listed ward(s) are in LTSB's filing for NO county "
              "(%s) — the two publishers differ on which wards exist, which is "
              "not evidence about district numbers; the ratio below is over the "
              "%d that both name"
              % (county, len(nowhere),
                 ", ".join("%s %s w%d" % k for k in nowhere)[:180], comparable),
              file=sys.stderr)
    if len(absent) > 0.25 * listed:
        raise RuntimeError("%s: %d of %d listed wards are absent from LTSB's filing "
                           "for this county — the document is describing a ward "
                           "fabric the state no longer has; re-read it"
                           % (county, len(absent), listed))
    if hit < 0.95 * comparable:
        raise RuntimeError("%s: only %d of %d listed wards that LTSB also has land "
                           "in its same-numbered district — the county's "
                           "composition and the state's filing no longer describe "
                           "one plan" % (county, hit, comparable))

    # THE MUNICIPALITY SET IS THE STRONGER TEST WHERE A DOCUMENT STATES IT, and
    # it is the one that reaches a district named whole. Every municipality the
    # county puts in district N must be exactly the set LTSB files there —
    # nothing extra, nothing missing — which is a statement about the NUMBERING
    # that survives the county listing wards loosely or not at all.
    if munis:
        filed = {}
        for f in feats:
            a = f.get("attributes") or {}
            filed.setdefault(int(a["SUPERID"]), set()).add(
                (str(a.get("CTV", "")).lower()[:1], _jk_norm(str(a.get("MCD_NAME", "")))))
        # SUBSET, NOT EQUALITY, and the difference is a real distinction rather
        # than a loosened bar. A county naming a municipality LTSB does NOT file
        # under that number is a CONFLICT: two publishers describing different
        # plans, which is exactly what this exists to catch. A county naming
        # FEWER is the document abbreviating — Pierce's directory lists the
        # towns of a rural district and leaves out the incorporated village
        # sitting inside it (Elmwood, Bay City, Maiden Rock, Plum City, and one
        # City of River Falls ward), 4 districts of 17, while every ward it DOES
        # name lands in LTSB's same-numbered district. Failing that would be
        # refusing a roster for saying less than the state, not for saying
        # something different. The shortfall is printed so it cannot go unseen.
        # A MUNICIPALITY PRESENT ONLY THROUGH A WARD LTSB DOES NOT HAVE IS THE
        # ABSENT-WARD CASE AGAIN, not a numbering conflict. Sawyer's District 11
        # names "Town of Hayward, Ward 8"; LTSB's Town of Hayward stops at ward
        # 7, so the municipality lands in the county's D11 set purely because of
        # a ward the state's filing has no row for. Counting that as two
        # publishers describing different plans refuses a county whose every
        # shared ward agrees. THE CHECK KEEPS ITS TEETH: a municipality the
        # county names WHOLE — no ward at all — that LTSB does not file under
        # that number is still a conflict, because there is no absent ward to
        # explain it; and so is one whose listed wards LTSB has but files
        # elsewhere.
        def _only_via_absent(d, key):
            here = {k for k in wards.get(d, set()) if k[:2] == key}
            return bool(here) and all(k not in exists for k in here)

        conflict = {}
        for d, v in munis.items():
            extra = sorted((k for k in v - filed.get(d, set())
                            if not _only_via_absent(d, k)), key=_order)
            if extra:
                conflict[d] = (extra, sorted(filed.get(d, set()), key=_order))
        if conflict:
            first = min(conflict)
            raise RuntimeError(
                "%s: %d of %d districts name a municipality LTSB does NOT file "
                "under that number — the two publishers describe different plans, "
                "or the document has been renumbered. First: D%s names %s, LTSB "
                "files %s" % (county, len(conflict), len(munis), first,
                              conflict[first][0], conflict[first][1]))
        short = sorted(d for d, v in munis.items() if filed.get(d, set()) - v)
        print("  witness %-12s %d/%d districts name only municipalities LTSB "
              "files there%s" % (county, len(munis), len(munis),
                                 "; %d abbreviate (%s)" % (len(short), ", ".join(
                                     "D%d" % d for d in short)) if short else ""),
              file=sys.stderr)


def scrape_pdf_roster_county(fips, county, seats, url):
    """All seats or nothing, out of the roster PDF the county's page links."""
    page = fetch(url)
    link = None
    for m in re.finditer(r'href="([^"]*\.pdf)"', page, re.I):
        href = html_lib.unescape(m.group(1)).strip()
        if re.search(r"(?i)county[_%20\s-]*board[_%20\s-]*members", href):
            link = urllib.parse.urljoin(url, href)
            break
    if not link:
        raise RuntimeError("%s: no County Board Members PDF linked from %s — the "
                           "county has renamed or moved its listing; re-read the "
                           "page" % (county, url))
    blob = fetch_bytes(link, timeout=90)[0]
    if not blob.startswith(b"%PDF"):
        raise RuntimeError("%s: %s did not return a PDF (%d bytes, starts %r)"
                           % (county, link, len(blob), blob[:16]))
    from pypdf import PdfReader           # noqa: PLC0415 - pinned, lazily imported
    reader = PdfReader(io.BytesIO(blob))
    lines = [l.strip() for p in reader.pages
             for l in (p.extract_text() or "").split("\n")]

    heads = [(i, int(m.group(1)), m.group(2))
             for i, l in enumerate(lines) for m in [JK_HEAD.match(l)] if m]
    seen = [d for _, d, _ in heads]
    if sorted(seen) != list(range(1, seats + 1)):
        raise RuntimeError("%s: the document's headings are %s, not 1..%d — "
                           "re-read %s" % (county, seen, seats, link))

    out, wards, emails, phones = {}, {}, 0, 0
    for n, (i, district, rest) in enumerate(heads):
        end = heads[n + 1][0] if n + 1 < len(heads) else len(lines)
        block = [l for l in lines[i + 1:end] if l]
        # the composition may WRAP past the heading line — see trap 2
        composition = rest
        for line in block:
            if not JK_WARDLINE.match(line):
                break
            composition += " " + line
        wards[district] = _jk_wards(composition)
        name = next((l for l in block
                     if not JK_WARDLINE.match(l) and is_name(l)), None)
        if not name:
            raise RuntimeError("%s: district %d resolved no name from its block "
                               "(%r) — re-read %s" % (county, district, block[:4], link))
        row = {"name": clean(name)[0], "vacant": False, "role": None}
        text = "\n".join(block)
        phone = PDF_PHONE.search(text)
        if phone:
            row["phone"] = "-".join(phone.groups())
            phones += 1
        mail = JK_MAIL.search(text)
        if mail and mail.group(0).lower().rsplit("@", 1)[-1] == JK_DOMAIN:
            row["email"] = mail.group(0)
            emails += 1
        out[str(district)] = row

    names = [r["name"] for r in out.values()]
    if len(set(names)) != len(names):
        dupes = sorted({n for n in names if names.count(n) > 1})
        raise RuntimeError("%s: the same person is filed under two districts (%s) "
                           "— the block boundaries have moved" % (county, dupes))
    if emails < JK_MIN_EMAILS or phones < JK_MIN_PHONES:
        raise RuntimeError("%s: %d e-mails and %d phones across %d seats (floors "
                           "%d/%d) — the document has reshaped and contact is "
                           "being dropped silently"
                           % (county, emails, phones, seats,
                              JK_MIN_EMAILS, JK_MIN_PHONES))
    ward_number_witness(fips, county, wards, seats)
    return out, link


# --- Clark: the County Clerk's OFFICIAL DIRECTORY, as a linked PDF ------------
#
# clarkcountywi.gov publishes no board page that names anybody. Its /county-board
# path 404s, and the COUNTY BOARD page inside the directory names three people:
# the Chairperson, the Vice Chairperson and the Clerk. A reader looking for the
# board stops there, and so did this project's record.
#
# THE NAMES ARE ELEVEN PAGES FURTHER IN. The Clerk compiles a 44-page Official
# Directory each term, and its "COUNTY SUPERVISORS - CLARK COUNTY / SUPERVISORY
# DISTRICTS" section prints all 29 seats as
#
#     District No. 4 (Town of Green Grove Ward 1, Town of Hoard Ward 2)
#     Tom Wilcox tom.wilcox@co.clark.wi.us ............................ 715-743-5225
#     N14016 Oak Grove Ave, Curtiss WI 54422
#
# — the district WITH ITS WARD COMPOSITION, then the person, then a HOME ADDRESS.
#
# FOUR THINGS ABOUT THIS DOCUMENT, EVERY ONE OF THEM MEASURED:
#
# 1. THE LINK IS DISCOVERED, NEVER PINNED. The county is on Wix and the document
#    is served from /_files/ugd/<hash>.pdf, a content hash that changes the day
#    the Clerk uploads a new edition. What is stable is the anchor TEXT in the
#    site's own nav — "Official Directory" — so that is what is matched, the
#    same discipline Adams's directory and Jackson's roster PDF already use.
#
# 2. THE SECTION SCOPE IS LOAD-BEARING. This one document also carries fifteen
#    TOWN boards (each with its own "Supervisor I / II"), the elected and
#    standing COMMITTEE rosters, and the county-board page naming the chair. An
#    unscoped parse mixes town supervisors into a county board, so the reader
#    starts at the SUPERVISORY DISTRICTS heading and stops at the next section.
#
# 3. pdfplumber, NOT pypdf's layout mode, and the reason is one row. pypdf
#    returns District 23 as "Duane Boonduaneboon5@gmail.com" — surname welded to
#    mailbox with no separator — which yields the name "Duane" and the address
#    "Boonduaneboon5@gmail.com". pdfplumber keeps the space. The name-shape
#    guard below catches the CLASS rather than that one row: a name carrying an
#    @, a digit, or fewer than two words fails the county rather than shipping.
#
# 4. THE THIRD LINE IS A HOME ADDRESS AND NEVER SHIPS. Every seat prints one,
#    and District 17's carries a second phone ("Cell: 715-613-8387") — which is
#    why the phone is read from the NAME line only and never from the block. A
#    home address is not contact data this project publishes, for any county.
#
# THE MAILBOXES ARE MOSTLY PERSONAL AND THEY STILL SHIP: three of the 29 are
# @co.clark.wi.us and the rest are gmail/yahoo/hotmail addresses the County
# Clerk publishes, in the county's official directory, as the way to reach that
# supervisor. That is a published constituent-contact channel for a public
# officeholder, which is exactly what the card exists to surface. The home
# addresses printed beside them are not, and are dropped.
CLARK_DIRECTORY = {
    "fips": "55019", "name": "Clark", "seats": 29,
    # the page a READER is sent to, and the page the link is discovered on
    "source_url": "https://www.clarkcountywi.gov/",
    "link_text": "Official Directory",
    # the county's own domain, for the log's own-vs-personal split
    "domain": "co.clark.wi.us",
}
CLARK_SECTION = re.compile(r"(?i)^SUPERVISORY\s+DISTRICTS?\s*$")
# "District No. 4 (Town of Green Grove Ward 1, Town of Hoard Ward 2)". The
# interposed "No." is why a plain /District\s+\d/ sweep of this document returns
# ONE hit — a committee page's "District 6" — and misses all 29 seats.
CLARK_HEAD = re.compile(r"^District No\.\s*(\d{1,2})\s*\((.*)\)\s*$")
CLARK_EMAIL = re.compile(r"(?<![^\s])([A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,})")
# Two or more words, letters and the punctuation a name really carries
# ("Joe Waichulis Jr", "DuWayne (Butch) Trunkel"). No digits, no @.
CLARK_NAME = re.compile(r"^[A-Za-z][A-Za-z.'\-]*(?: \(?[A-Za-z][A-Za-z.'\-]*\)?)+$")
# "Tom Wilcox, Chairperson" on the directory's own COUNTY BOARD page
CLARK_ROLE = re.compile(r"^([A-Z][A-Za-z.'\- ]+?),\s*((?:Vice\s+)?Chair(?:person|man|woman)?)\s*$")
# Shared by every county whose document states its districts in prose.
MUNI_RE = re.compile(r"(?i)\b(city|town|village)\s+of\s+([A-Za-z][A-Za-z .'\-]*?)"
                     r"(?=\s+(?:city|town|village)\s+of\b|\s*,?\s+Wards?\b|\s*,|\s*&|\s*$|\s+and\b)")
WARDS_RE = re.compile(r"(?i)wards?\s*((?:\d+\s*(?:,|&|and)?\s*)+)")
CLARK_MIN_EMAILS = 16    # 20 of 29 publish one today
CLARK_MIN_PHONES = 26    # 28 of 29 today; District 18 prints none
# 56 numbered (municipality, ward) pairs today. Six districts name a
# municipality WHOLE and contribute none, which is why this is not 2x seats.
CLARK_MIN_WARD_PAIRS = 45


def _clark_lines(blob):
    """The directory's printed lines, via pdfplumber — see note 3 above."""
    import io                            # noqa: PLC0415
    import pdfplumber                    # noqa: PLC0415 - pinned in requirements
    out = []
    with pdfplumber.open(io.BytesIO(blob)) as pdf:
        for page in pdf.pages:
            out += (page.extract_text() or "").split("\n")
    return [re.sub(r"\s+", " ", ln).strip() for ln in out]


# A composition can name several municipalities under ONE "of", with or without
# per-item wards: Marathon writes "Towns of Harrison, Hewitt, Easton, Plover,
# Norrie Ward 1 & Village of Birnamwood" and "Cities of Abbotsford and Colby".
# So a type word opens a RUN, and the run is a list of items until the next type
# word. Clark's and Pierce's singular forms are the one-item case of this.
TYPE_RUN = re.compile(r"(?i)\b(cit(?:y|ies)|towns?|villages?)\s+of\s+")
TYPE_LETTER = {"city": "c", "cities": "c", "town": "t", "towns": "t",
               "village": "v", "villages": "v"}
# A name never STARTS with the separator word "and": without the guard,
# "Village of Rothschild Wards 5 & 6 and Weston Ward 1" yields a municipality
# called "and Weston". Names themselves may contain spaces (Rib Mountain,
# Green Valley, Eau Pleine) and even a type word (Village of MARATHON CITY),
# which is safe because a type word only opens a run when "of" follows it.
# A WARD RUN IS MASKED BEFORE ITEMS ARE SPLIT, because its separators are the
# item separators. "Wards 2, 3 & 4" is ONE item's wards and "Berlin Ward 1,
# Stettin Ward 4" is TWO items; splitting first gets both wrong. The run is
# digits joined only by separators that are followed by more digits, so
# "Ward 11, Hatley" masks "Ward 11" and leaves the comma to separate items.
# The optional LEADING COMMA is Pierce ("Town of Martell, Ward 2 Town of River
# Falls, Wards 1, 2 & 3"), where a comma sits between the name and its wards and
# is NOT an item separator. The optional digits are Clark, whose District 27
# reads "Town of Grant Ward," with no number at all — masking it keeps the bare
# word out of the municipality name.
# THE RUN CONTINUES ACROSS THE WORD "and", NOT ONLY ACROSS PUNCTUATION. This
# accepted , & – and - between the numbers of one ward run and not "and", so
# Sawyer's "City of Hayward Wards 5 and 6" matched as "Wards 5" alone: ward 6
# fell out of the run, COMP_SEP then split the leftover " and 6" into a part
# with no municipality name, and the pair was DROPPED SILENTLY. Nothing shipped
# wrong — the pairs found were right — but every "N and M" county was witnessed
# on half its wards while the log printed a confident hit/listed ratio over the
# smaller number. _ward_numbers() below already split on "and"; it was never
# reached with the second number.
COMP_WARDS = re.compile(
    r"(?i),?\s*\bWards?\b(?:\s*\d+(?:\s*(?:[,&\u2013-]|\band\b)\s*\d+)*)?")
COMP_SEP = re.compile(r"(?i)[,;&]|\band\b")


def _ward_numbers(text):
    """{1, 2, 3} for "Wards 1, 2 & 3" or "Wards 1-3" — Marathon writes both.

    Takes the WHOLE run including its leading "Ward"/"Wards", which is stripped
    here rather than by the caller: leaving it on silently drops the FIRST ward
    of every list, because "Wards 2" is not a number.
    """
    out = set()
    for chunk in re.split(r"[,&]|\band\b", re.sub(r"(?i)^[\s,]*Wards?\s*", "", text or "")):
        chunk = chunk.strip()
        span = re.fullmatch(r"(\d+)\s*[-\u2013]\s*(\d+)", chunk)
        if span:
            lo, hi = int(span.group(1)), int(span.group(2))
            if 0 < lo <= hi <= 200:
                out.update(range(lo, hi + 1))
        elif chunk.isdigit():
            out.add(int(chunk))
    return out


def parse_composition(composition):
    """({(type, municipality, ward)}, {(type, municipality)}) for one district.

    THE TYPE IS PART OF THE KEY, and Pierce is why. Wisconsin lets a town and a
    village of the same name sit side by side, each with its own ward 1: Pierce
    has Ellsworth wards 1 and 2 as BOTH a Town and a Village, in two different
    supervisory districts, and Marathon carries five such pairs (Elderon,
    Mosinee, Spencer, Wausau, Weston). Keyed on the bare name, one of those
    scores a match for whichever it meets first — a coin-flip dressed as
    agreement.

    A municipality named with NO ward means the whole municipality and
    contributes no ward pair; it still contributes its (type, name), which is
    what the municipality-set check uses.
    """
    pairs, munis = set(), set()
    runs = [(m.end(), TYPE_LETTER[m.group(1).lower()])
            for m in TYPE_RUN.finditer(composition)]
    starts = [m.start() for m in TYPE_RUN.finditer(composition)]
    for n, (begin, ctv) in enumerate(runs):
        end = starts[n + 1] if n + 1 < len(starts) else len(composition)
        seg = composition[begin:end]
        runs, masked = [], seg
        for m in reversed(list(COMP_WARDS.finditer(seg))):
            runs.append(m.group(0))
            masked = masked[:m.start()] + ("\x00%d\x00" % (len(runs) - 1)) + masked[m.end():]
        for part in COMP_SEP.split(masked):
            tok = re.search(r"\x00(\d+)\x00", part)
            name = _jk_norm(re.sub(r"\x00\d+\x00", " ", part))
            if not name:
                continue
            munis.add((ctv, name))
            if tok:
                for w in _ward_numbers(runs[int(tok.group(1))]):
                    pairs.add((ctv, name, w))
    return pairs, munis


def scrape_official_directory_county(spec):
    """All seats or nothing, out of the Clerk's own Official Directory PDF."""
    county, seats = spec["name"], spec["seats"]
    page = fetch(spec["source_url"])
    link = None
    for m in re.finditer(r'href="([^"]+\.pdf)"[^>]*>\s*([^<]{1,60}?)\s*<', page, re.I):
        if html_lib.unescape(m.group(2)).strip().lower() == spec["link_text"].lower():
            link = urllib.parse.urljoin(spec["source_url"],
                                        html_lib.unescape(m.group(1)).strip())
            break
    if not link:
        raise RuntimeError("%s: no %r PDF link on %s — the county has renamed or "
                           "moved its directory; re-read the page"
                           % (county, spec["link_text"], spec["source_url"]))
    blob = fetch_bytes(link, timeout=90)[0]
    if not blob.startswith(b"%PDF"):
        raise RuntimeError("%s: %s did not return a PDF (%d bytes, starts %r)"
                           % (county, link, len(blob), blob[:16]))
    lines = _clark_lines(blob)

    start = next((i for i, l in enumerate(lines) if CLARK_SECTION.match(l)), None)
    if start is None:
        raise RuntimeError("%s: the directory carries no SUPERVISORY DISTRICTS "
                           "heading — it has been restructured; re-read %s"
                           % (county, link))
    heads = [(i, m) for i, l in enumerate(lines[start:], start)
             for m in [CLARK_HEAD.match(l)] if m]
    seen = [int(m.group(1)) for _, m in heads]
    if sorted(seen) != list(range(1, seats + 1)):
        raise RuntimeError("%s: the directory's district headings are %s, not "
                           "1..%d — re-read %s" % (county, seen, seats, link))

    out, wards, munis, emails, phones, own = {}, {}, {}, 0, 0, 0
    for i, m in heads:
        district = int(m.group(1))
        wards[district], munis[district] = parse_composition(m.group(2))
        if not munis[district]:
            raise RuntimeError("%s: district %d's heading names no municipality "
                               "(%r) — the composition is what witnesses the "
                               "numbering, so this cannot ship unchecked"
                               % (county, district, m.group(2)[:80]))
        line = lines[i + 1]
        mail = CLARK_EMAIL.search(line)
        # THE NAME LINE ONLY: District 17's home-address line carries a second
        # phone, and reading the block would ship it as the listed number.
        phone = PDF_PHONE.search(line)
        name = line
        for cut in (mail.group(1) if mail else None, phone.group(0) if phone else None):
            if cut:
                name = name.split(cut)[0]
        name = clean(name.split("....")[0].strip(" ."))[0]
        if not CLARK_NAME.match(name):
            raise RuntimeError("%s: district %d resolved the name %r from %r — "
                               "that is not a name, and the row has reshaped; "
                               "re-read %s" % (county, district, name, line[:90], link))
        row = {"name": name, "vacant": False, "role": None}
        if phone:
            row["phone"] = "-".join(phone.groups())
            phones += 1
        if mail:
            row["email"] = mail.group(1)
            emails += 1
            own += mail.group(1).lower().endswith("@" + spec["domain"])
        out[str(district)] = row

    names = [r["name"] for r in out.values()]
    if len(set(names)) != len(names):
        dupes = sorted({n for n in names if names.count(n) > 1})
        raise RuntimeError("%s: the same person is filed under two districts (%s) "
                           "— the heading boundaries have moved" % (county, dupes))
    if emails < CLARK_MIN_EMAILS or phones < CLARK_MIN_PHONES:
        raise RuntimeError("%s: %d e-mails and %d phones across %d seats (floors "
                           "%d/%d) — the directory has reshaped and contact is "
                           "being dropped silently"
                           % (county, emails, phones, seats,
                              CLARK_MIN_EMAILS, CLARK_MIN_PHONES))

    # The directory's own COUNTY BOARD page names the Chairperson and Vice
    # Chairperson without their districts; the seats above give the districts
    # without the roles. Joined on a name that must appear EXACTLY once.
    for j, l in enumerate(lines[:start]):
        r = CLARK_ROLE.match(l)
        if not r or "County Board" not in " ".join(lines[j + 1:j + 3]):
            continue
        who, role = clean(r.group(1))[0], r.group(2).title()
        hits = [d for d, row in out.items() if row["name"] == who]
        # THE TWO SECTIONS OF ONE DOCUMENT SPELL ONE MAN TWO WAYS, and the 2026
        # edition is where it first bit: the board page calls the chair "Ken
        # Gerhardt" and the district list eleven pages later prints "Kenneth
        # Gerhardt" (District 25), so the exact-name join matched 0 seats and
        # the county — all 29 seats of it, correctly parsed — refused to ship.
        # This is the Clay County (IL) trap arriving in Wisconsin: there a board
        # page's "Barbara McGrew" is a members page's "Barb Mcgrew", and the
        # answer there is the answer here — JOIN ON THE SURNAME, REQUIRE IT
        # UNIQUE, AND PRINT THE JOIN so a reader of the weekly log sees which
        # two strings were treated as one person.
        #
        # Uniqueness is load-bearing rather than ceremonial: Clark seats TWO
        # Ashbecks (districts 20 and 26), so a surname that is not unique still
        # falls through to the same refusal below. A chair who has genuinely
        # left the board matches no surname either, and also still refuses.
        if not hits:
            hits = [d for d, row in out.items()
                    if _surname(row["name"]) == _surname(who)]
            if len(hits) == 1:
                print("  role    %-12s the board page's %r is the district list's "
                      "%r — joined on a unique surname"
                      % (county, who, out[hits[0]]["name"]), file=sys.stderr)
        if len(hits) != 1:
            raise RuntimeError("%s: the directory's board page calls %r the %s "
                               "and the district list matches %d seats, by full "
                               "name or by surname — a role cannot be filed "
                               "without one" % (county, who, role, len(hits)))
        out[hits[0]]["role"] = role
        print("  role    %-12s %s -> District %s" % (county, role, hits[0]), file=sys.stderr)

    print("  %-12s %d seats, %d phones, %d e-mails (%d on %s, %d personal but "
          "county-published)" % (county, seats, phones, emails, own,
                                 spec["domain"], emails - own), file=sys.stderr)
    ward_number_witness(spec["fips"], county, wards, seats,
                        min_pairs=CLARK_MIN_WARD_PAIRS, munis=munis)
    return out, link


# --- Pierce: the Clerk's annual county DIRECTORY, pinned because robots.txt --
#     forbids reading the page that would otherwise link it -------------------
#
# Pierce's directory is the richest board document in this fleet: every seat
# prints its municipalities and wards, the supervisor, a phone, a
# firstname.lastname county mailbox, when they were elected or appointed, and
# their committees. It is also the first whose link CANNOT be discovered, and
# that is a robots decision rather than a technical one.
#
# www.co.pierce.wi.us REDIRECTS to cms5.revize.com, so the county's pages and
# its documents share one policy, and that policy is:
#
#     User-agent: *
#     Allow: /*.pdf$   (and .DOC/.DOCX/.PPT/.PPTX)
#     Disallow: /
#
# Documents yes, pages no. So there is no listing page this may read to find
# the current file, and the URL is pinned instead — the exact opposite of
# Clark, where the hash-named file forced discovery. What makes the pin
# survivable is that the county names the file by YEAR and keeps exactly one:
# 2024 and 2025 both 404 today and 2026 answers. So the fetch tries this year,
# next year and last year against the same template, which self-heals at the
# turn of the year and is three permitted .pdf requests rather than a crawl.
#
# THAT POLICY ALSO CAUGHT A BUG IN THIS PROJECT'S OWN ROBOTS GATE, which had
# been doing literal prefix matching and so could not match a pattern
# containing `*` or `$` AT ALL. It read this file as a flat refusal. Wildcards
# are RFC 9309 section 2.2.3 and every major crawler implements them; the gate
# does now too, and the same blindness ran the other way — a wildcard DISALLOW
# covering a fetched path would have been silently ignored.
#
# TWO WITNESSES, BOTH INSIDE THE COUNTY'S OWN MATERIAL:
#
# 1. THE MAILBOX IS THE NAME. Every seat publishes firstname.lastname@
#    co.pierce.wi.us, so the heading's name is checked against its own mailbox
#    — 17 of 17 agree. That is what makes a two-column PDF safe to read: the
#    name is reconstructed from a line whose halves the layout splits, and the
#    mailbox says whether the reconstruction was right.
# 2. THE ROTATED INDEX. Page 18 is a sideways summary listing all 17 districts
#    with an initial and a surname, which pdfplumber returns character-reversed
#    ("ytraCcM"). Reversed back it agrees with all 17 blocks, and it is where
#    the display spelling of McCARTY comes from: the fleet's title_case is
#    documented as getting Mc/Mac and apostrophes wrong, and its own note says
#    such a name needs an EXPLICIT label with a source. This is that source —
#    the county's own mixed-case rendering, in the same document.
#
# THE HOME ADDRESSES DO NOT SHIP. They occupy the right-hand column of every
# block, which is exactly why the columns are split by x-position rather than
# by flattening the page: a flattened line reads
# "City of Prescott 611 Lake St. N." and there is no honest way to tell the
# composition from the address afterwards.
PIERCE_DIRECTORY = {
    "fips": "55093", "name": "Pierce", "seats": 17,
    "source_url": "https://www.co.pierce.wi.us/",
    "doc_template": ("https://cms5.revize.com/revize/piercewi/Agendas%%20and%%20Minutes/"
                     "Government/Board%%20of%%20Supervisor/"
                     "%d%%20Directory_Pierce%%20County.pdf"),
    "domain": "co.pierce.wi.us",
    "pages": (15, 22),          # 0-based slice of the board section
    "index_page": 17,           # the rotated summary
}
# Word x0 below this is the composition column; at or above it is the address
# and phone column. Measured on a 306pt-wide page: composition words sit at
# 35-110 and the address column starts at 185.
PIERCE_SPLIT = 180.0
PIERCE_HEAD = re.compile(r"^District\s+(\d{1,2})\s*\.{3,}\s*(.+?)\s*$")
PIERCE_STOP = re.compile(r"(?i)\b(Email|Elected|Appointed|Committees|Term)\b")
PIERCE_PHONE = re.compile(r"\(?(\d{3})\)?[-.\s]\s*(\d{3})[-.\s](\d{4})")
# "Chairperson ....... Jon Aubart" / "2nd Vice-Chairperson ....... Neil Gulbranson"
PIERCE_ROLE = re.compile(r"^((?:2nd\s+)?(?:Vice-)?Chairperson)\s*\.{3,}\s*(.+?)\s*$")
PIERCE_MIN_EMAILS = 15   # 17 of 17 today
PIERCE_MIN_PHONES = 15   # 17 of 17 today
# 44 typed (type, municipality, ward) pairs today; several districts name a
# municipality WHOLE and contribute none, so this is not 2x seats.
PIERCE_MIN_WARD_PAIRS = 34


def _pierce_rows(pdf, first, last):
    """[(whole line, left column, right column)] for the board section."""
    import collections                  # noqa: PLC0415
    out = []
    for page in pdf.pages[first:last]:
        buckets = collections.defaultdict(list)
        for w in page.extract_words():
            buckets[round(w["top"] / 3)].append(w)
        for k in sorted(buckets):
            ws = sorted(buckets[k], key=lambda w: w["x0"])
            out.append((" ".join(w["text"] for w in ws),
                        " ".join(w["text"] for w in ws if w["x0"] < PIERCE_SPLIT).strip(),
                        " ".join(w["text"] for w in ws if w["x0"] >= PIERCE_SPLIT).strip()))
    return out


def _pierce_index(pdf, page_no):
    """{district: (initial, Surname)} from the sideways summary on page 18.

    The page is rendered bottom-to-top, so every token comes back reversed;
    reversing each one restores it. The stream is number, surname, initial.
    """
    toks = [l[::-1] for l in (pdf.pages[page_no].extract_text() or "").split("\n") if l.strip()]
    table, i = {}, 0
    while i < len(toks) - 2:
        if re.fullmatch(r"\d{1,2}", toks[i]) \
           and re.fullmatch(r"[A-Z][A-Za-z'\-]+", toks[i + 1]) \
           and re.fullmatch(r"[A-Z]\.", toks[i + 2]):
            table[int(toks[i])] = (toks[i + 2], toks[i + 1])
            i += 3
        else:
            i += 1
    return table


def scrape_pierce_directory(spec):
    """All seats or nothing, out of the county's pinned annual directory PDF."""
    import io                           # noqa: PLC0415
    import pdfplumber                   # noqa: PLC0415 - pinned in requirements
    county, seats = spec["name"], spec["seats"]
    year = int(time.strftime("%Y"))
    blob, link, tried = None, None, []
    for candidate in (year, year + 1, year - 1):
        url = spec["doc_template"] % candidate
        tried.append(str(candidate))
        try:
            body = fetch_bytes(url, timeout=120)[0]
        except Exception:               # noqa: BLE001 - a 404 is the next year
            continue
        if body.startswith(b"%PDF"):
            blob, link = body, url
            break
    if blob is None:
        raise RuntimeError("%s: no directory PDF answered for %s — the county has "
                           "renamed the file or changed its path, and robots.txt "
                           "forbids reading the page that links it, so the URL in "
                           "PIERCE_DIRECTORY has to be re-pinned by hand"
                           % (county, "/".join(tried)))
    if link != spec["doc_template"] % year:
        print("  note %-12s directory is the %s edition, not %d"
              % (county, link.rsplit("/", 1)[-1][:4], year), file=sys.stderr)

    with pdfplumber.open(io.BytesIO(blob)) as pdf:
        rows = _pierce_rows(pdf, *spec["pages"])
        index = _pierce_index(pdf, spec["index_page"])
    heads = [(i, m) for i, (full, _, _) in enumerate(rows)
             for m in [PIERCE_HEAD.match(full)] if m]
    seen = [int(m.group(1)) for _, m in heads]
    if sorted(seen) != list(range(1, seats + 1)):
        raise RuntimeError("%s: the directory's district headings are %s, not "
                           "1..%d — re-read %s" % (county, seen, seats, link))
    if sorted(index) != list(range(1, seats + 1)):
        raise RuntimeError("%s: the summary index lists districts %s, not 1..%d — "
                           "the page that cross-checks every seat has moved or "
                           "reshaped; re-read %s" % (county, sorted(index), seats, link))

    mail_re = re.compile(r"([A-Za-z0-9._%+\-]+)@" + re.escape(spec["domain"]) + r"\b", re.I)
    out, wards, munis, emails, phones = {}, {}, {}, 0, 0
    for n, (i, m) in enumerate(heads):
        end = heads[n + 1][0] if n + 1 < len(heads) else len(rows)
        district, raw_name = int(m.group(1)), " ".join(m.group(2).split())
        comp, phone, email, collecting = [], None, None, True
        for full, left, right in rows[i + 1:end]:
            if PIERCE_STOP.search(full):
                collecting = False
            if not email:
                em = mail_re.search(full)
                if em:
                    email = em.group(0).lower()
            # THE PHONE COMES FROM THE ADDRESS COLUMN AND MUST BE LABELLED.
            # Unlabelled digits over there are a street number or a ZIP.
            if not phone:
                ph = PIERCE_PHONE.search(right)
                if ph and re.search(r"(?i)\b(cell|home|phone|work)\b", right):
                    phone = "-".join(ph.groups())
            if collecting and left:
                comp.append(left)
        if not email:
            raise RuntimeError("%s: district %d publishes no %s mailbox — that "
                               "mailbox is what witnesses the name a two-column "
                               "layout reconstructs, so this cannot ship "
                               "unchecked; re-read %s" % (county, district,
                                                          spec["domain"], link))
        parts = {p for p in re.split(r"[._]", mail_re.match(email).group(1)) if p}
        words = {w.lower().strip(".") for w in raw_name.split()}
        if not parts <= words:
            raise RuntimeError("%s: district %d reads the name %r beside the "
                               "mailbox %r — the two halves of the heading line "
                               "have not been put back together correctly; "
                               "re-read %s" % (county, district, raw_name, email, link))
        initial, surname = index[district]
        if raw_name.split()[0][0].upper() + "." != initial \
           or raw_name.split()[-1].lower() != surname.lower():
            raise RuntimeError("%s: district %d reads %r and the directory's own "
                               "summary index says %s %s — the two disagree, and "
                               "neither is guessed at; re-read %s"
                               % (county, district, raw_name, initial, surname, link))
        # The index carries the county's own mixed-case spelling (McCarty),
        # which the fleet's title_case is documented as unable to derive.
        given = " ".join(w.capitalize() for w in raw_name.split()[:-1])
        out[str(district)] = {"name": ("%s %s" % (given, surname)).strip(),
                              "vacant": False, "role": None,
                              "email": email}
        emails += 1
        if phone:
            out[str(district)]["phone"] = phone
            phones += 1
        wards[district], munis[district] = parse_composition(" ".join(comp))
        if not munis[district]:
            raise RuntimeError("%s: district %d's block names no municipality — "
                               "the composition is what witnesses the numbering, "
                               "so this cannot ship unchecked; re-read %s"
                               % (county, district, link))

    names = [r["name"] for r in out.values()]
    if len(set(names)) != len(names):
        dupes = sorted({n for n in names if names.count(n) > 1})
        raise RuntimeError("%s: the same person is filed under two districts (%s)"
                           % (county, dupes))
    if emails < PIERCE_MIN_EMAILS or phones < PIERCE_MIN_PHONES:
        raise RuntimeError("%s: %d e-mails and %d phones across %d seats (floors "
                           "%d/%d) — the directory has reshaped and contact is "
                           "being dropped silently"
                           % (county, emails, phones, seats,
                              PIERCE_MIN_EMAILS, PIERCE_MIN_PHONES))

    # The board's officers are printed above the seats, WITHOUT their districts,
    # and the two surfaces do not agree on given names — the officer line says
    # "Mike Kahlow" where the seat says "MICHAEL KAHLOW" — so the join is on a
    # surname that must match exactly one seat.
    by_surname = {}
    for d, row in out.items():
        by_surname.setdefault(row["name"].split()[-1].lower(), []).append(d)
    for full, _, _ in rows:
        r = PIERCE_ROLE.match(full)
        if not r:
            continue
        role, who = r.group(1), " ".join(r.group(2).split())
        hits = by_surname.get(who.split()[-1].lower(), [])
        if len(hits) != 1:
            raise RuntimeError("%s: the board page calls %r the %s and that "
                               "surname matches %d seats — a role is never filed "
                               "without one" % (county, who, role, len(hits)))
        out[hits[0]]["role"] = role
        print("  role    %-12s %-22s -> District %s" % (county, role, hits[0]),
              file=sys.stderr)

    print("  %-12s %d seats, %d phones, %d county mailboxes"
          % (county, seats, phones, emails), file=sys.stderr)
    ward_number_witness(spec["fips"], county, wards, seats,
                        min_pairs=PIERCE_MIN_WARD_PAIRS, munis=munis)
    return out, link


# --- Marathon: the county's staff-directory table, plus one page per member ---
#
# Marathon seats 38, the largest board in Wisconsin, and it was the last county
# this project's own ask-queue still listed as needing a letter. It never did.
# Two things had been recorded about it and both were half-true:
#
#   "Marathon answers 403 to this client."  Its Akamai edge does — to a browser
#   User-Agent, to no User-Agent, to an honest one, and to curl's default, all
#   with the same 428-byte deny. It does NOT to the header set this file already
#   sends for Monroe (UA + Accept + Accept-Language + Sec-Fetch-*), which
#   Akamai's bot scoring treats as a real navigation. Even robots.txt is denied
#   without it. So the county was never blocked to this project; it was blocked
#   to four clients nobody here uses.
#
#   "Marathon has no pinned reading yet."  That was the accurate half, and it is
#   what this fixes.
#
# THE MEMBERS PAGE LOOKS LIKE A MAP INDEX AND IS NOT ONE. Its only visible
# widget is "District Maps" — 38 links to per-district PDFs with no person on
# them, the exact shape this project already records for Kenosha, Oconto and
# Ozaukee and warns to test for the PEOPLE rather than the district numbers.
# The people are in a staff-directory table further down the same document:
# 38 rows of Surname-first name, "DISTRICT n", a phone, and an e-mail link.
#
# THE E-MAIL IS NOT SHIPPED, AND THAT IS A DECISION RATHER THAN A LIMITATION.
# Every address sits behind a JavaScript handler keyed by `data-mailto-id`, on
# the table AND on each member's own page; no @marathoncounty.gov string exists
# in either document. That is deliberate anti-harvesting, and defeating it is
# the same class of act as answering a captcha, which this project does not do.
# So the card carries the name, the district, the phone the county publishes in
# plain markup, and a link to the member's own page where a reader can click
# through to write to them.
#
# EACH MEMBER'S PAGE IS FETCHED, and it earns the trip twice: it states that
# member's own "Title: DISTRICT n" — the list-versus-own-page agreement the
# Oconto reader already relies on — and it prints the district's WARD
# COMPOSITION, which is what lets ward_number_witness check the numbering
# against LTSB's filing. It also prints the member's HOME ADDRESS, which is
# read past and never shipped.
#
# TWO THINGS THE WITNESS REPORTS RATHER THAN SWALLOWS, both measured 2026-09-02.
# District 37's page calls Rib Mountain a TOWN where District 36's calls it a
# VILLAGE and the state files it as a village; the two districts' ward numbers
# (1,2,7,8,9 against 3,4,5,6,10) match LTSB exactly, so the word is a stale
# label and the numbers decide. And three City of Marshfield wards read 1-3 here
# where LTSB files 12, 16 and 19: Marshfield straddles Marathon and Wood, and
# the county numbers its own share while the state uses the city's numbering.
# Both publishers put Marshfield in District 27, so the numbering is not in
# doubt — 90 of 93 ward pairs land, and the three that do not are named in the
# run's own log rather than absorbed by a threshold.
MARATHON_DIRECTORY = {
    "fips": "55073", "name": "Marathon", "seats": 38,
    "source_url": "https://www.marathoncounty.gov/about-us/government/county-board/members",
    "origin": "https://www.marathoncounty.gov",
}
# "<td><a href="/Home/Components/StaffDirectory/StaffDirectory/2035/62">Rosenberg,
#  Katie</a></td><td class="mobile_hide">DISTRICT 1</td><td><a ... tel:7152123477"
MARATHON_ROW = re.compile(
    r'(?is)<td>\s*<a href="(?P<url>/Home/Components/StaffDirectory/StaffDirectory/\d+/\d+)">'
    r'(?P<name>[^<]+)</a>\s*</td>\s*'
    r'<td[^>]*>\s*DISTRICT\s+(?P<district>\d{1,2})\s*</td>'
    r'(?:(?!</tr>).)*?href=.tel:(?P<phone>\d{10})')
MARATHON_TITLE = re.compile(r"(?i)Title:\s*\|\s*DISTRICT\s+(\d{1,2})\b")
# "(City of Wausau Wards 1, 2)" — parenthesised, and the ONLY thing taken from a
# page that also prints a street address two lines above it.
MARATHON_COMP = re.compile(r"\(([^()]*(?:City|Town|Village)s?\s+of[^()]*)\)", re.I)
MARATHON_MIN_PHONES = 34    # 38 of 38 today
MARATHON_MIN_WARD_PAIRS = 70    # 93 today


def _marathon_text(html):
    """One flattened line of a member page, tags collapsed to pipes."""
    body = re.sub(r"(?is)<(script|style).*?</\1>", " ", html)
    body = html_lib.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " | ", body)))
    return re.sub(r"(\| )+", "| ", body)


def scrape_marathon_directory(spec):
    """All seats or nothing: the table for the roster, each page for the proof."""
    county, seats = spec["name"], spec["seats"]
    page = fetch(spec["source_url"])
    rows = list(MARATHON_ROW.finditer(page))
    seen = [int(m.group("district")) for m in rows]
    if sorted(seen) != list(range(1, seats + 1)):
        raise RuntimeError("%s: the members table lists districts %s, not 1..%d — "
                           "the page has reshaped; re-read %s"
                           % (county, seen, seats, spec["source_url"]))

    out, wards, munis, phones = {}, {}, {}, 0
    for n, m in enumerate(rows):
        district = int(m.group("district"))
        # SURNAME FIRST — "Rosenberg, Katie" — flipped, and the flip PRINTED,
        # because a table that stops using the comma would otherwise ship every
        # name backwards without a word.
        raw = html_lib.unescape(m.group("name")).strip()
        if "," not in raw:
            raise RuntimeError("%s: district %d reads the name %r, which is not "
                               "'Surname, Given' — the table has changed how it "
                               "writes names and the flip below would be wrong"
                               % (county, district, raw))
        surname, given = (p.strip() for p in raw.split(",", 1))
        name = clean("%s %s" % (given, surname))[0]
        row = {"name": name, "vacant": False, "role": None,
               "phone": "%s-%s-%s" % (m.group("phone")[:3], m.group("phone")[3:6],
                                      m.group("phone")[6:])}
        phones += 1

        if n:
            time.sleep(0.4)             # 38 pages of somebody else's server
        profile = fetch(spec["origin"] + m.group("url"))
        text = _marathon_text(profile)
        own = MARATHON_TITLE.search(text)
        if not own:
            raise RuntimeError("%s: %s's own page states no 'Title: DISTRICT n' — "
                               "that statement is what confirms the table's "
                               "district, so this cannot ship unchecked (%s)"
                               % (county, name, spec["origin"] + m.group("url")))
        if int(own.group(1)) != district:
            raise RuntimeError("%s: the table files %s under district %d and their "
                               "own page says district %s — the two county "
                               "surfaces disagree, and neither is guessed at"
                               % (county, name, district, own.group(1)))
        comp = MARATHON_COMP.search(text)
        if not comp:
            raise RuntimeError("%s: %s's page prints no ward composition — that "
                               "composition is what witnesses the numbering "
                               "against the state's filing (%s)"
                               % (county, name, spec["origin"] + m.group("url")))
        wards[district], munis[district] = parse_composition(comp.group(1))
        if not munis[district]:
            raise RuntimeError("%s: district %d's composition %r names no "
                               "municipality" % (county, district, comp.group(1)[:80]))
        row["profileUrl"] = spec["origin"] + m.group("url")
        out[str(district)] = row

    names = [r["name"] for r in out.values()]
    if len(set(names)) != len(names):
        dupes = sorted({n for n in names if names.count(n) > 1})
        raise RuntimeError("%s: the same person is filed under two districts (%s)"
                           % (county, dupes))
    if phones < MARATHON_MIN_PHONES:
        raise RuntimeError("%s: %d phones across %d seats (floor %d) — the table "
                           "has reshaped and contact is being dropped silently"
                           % (county, phones, seats, MARATHON_MIN_PHONES))
    print("  %-12s %d seats, %d phones, 0 e-mails (every address is behind the "
          "county's JavaScript mailto handler and is not taken)"
          % (county, seats, phones), file=sys.stderr)
    ward_number_witness(spec["fips"], county, wards, seats,
                        min_pairs=MARATHON_MIN_WARD_PAIRS, munis=munis)
    return out, spec["source_url"]


# --- St. Croix: the county's own Districts & Supervisors table ----------------
#
# THE RECORD SAID THIS COUNTY PUBLISHES NOTHING, AND THE MEASUREMENT BEHIND
# THAT WAS OF THE WRONG PAGE — the sixth county in this fleet to sit dark for
# that reason after Jackson, Waupaca, Oconto, Taylor and Marathon.
#
# St. Croix has never been blocked: sccwi.gov answers 200 to the plain client
# and its robots.txt permits everything outside /admin, /search and /map. What
# it does NOT do is link its board from its home page — and the home page is
# the URL this repo itself had on file for the county, in
# build_wi_county_board_directory.py's table and therefore on the card's own
# footer link. Zero anchors on sccwi.gov/ match board, supervisor or district.
# The route is Government -> County Board of Supervisors -> Districts &
# Supervisors, and the middle page is the trap: /477 is four paragraphs of
# prose that states "19 elected supervisors that each represent one of the 19
# districts" and names NOT ONE of them, which is precisely the sentence the gap
# record used ("publishes prose with no district column"). That description was
# accurate about /477 and false about the county, whose /483 page one link
# further carries all nineteen with their wards, phones and county mailboxes.
#
# A COUNTY'S BOARD LANDING PAGE DESCRIBES THE BOARD; THE ROSTER IS ONE LINK
# DEEPER, under a Districts, Members or More Resources heading. That is the
# generalisable form of the Oconto and Marathon findings, and it is why the
# card's footer link moves to /477 in this same change: a reader sent to the
# county's front door cannot reach their own board either.
#
# THE TABLE IS THE BEST-SHAPED SOURCE IN WISCONSIN. Five columns — district,
# municipal wards, standing committees, the supervisor's contact block, and
# when they were first elected — as a real <table> with one <tr> per district,
# every e-mail a plain mailto: in the markup, and the ward composition printed
# beside the number. It witnesses at 131 of 131 wards and 19 of 19
# municipality sets against LTSB's own filing, with no relabel and no stray
# pair: the cleanest ward witness this project has run.
#
# THREE THINGS ARE DELIBERATELY NOT TAKEN.
#
#   THE ADDRESS BLOCK. Every contact cell prints a street address under the
#   name, and the county mixes two kinds in one column: eleven supervisors
#   list 1101 Carmichael Road, which is the Government Center, and eight list
#   what is plainly their home. No column, tag or class separates them — only
#   knowing the county's own address does — so nothing here reads the address
#   at all. That is the Pierce decision reached by a different route: there the
#   two were separable by position on the page and the home column was
#   discarded; here they are not separable, so both go.
#
#   THE SHARED PHONE. Districts 7, 10, 13 and 19 all print 715-386-4610, which
#   the county's own staff directory gives as County Clerk Christine Hines's
#   line. Those four publish no personal number and the table falls back to a
#   county office. drop_shared_phones() drops it from all four and names it on
#   the log — the generic rule, not a pin on that number.
#
#   THE COMMITTEE AND FIRST-ELECTED COLUMNS. Both are real and neither has a
#   row on any county-board card in the fleet. Adding a field nineteen records
#   out of 1,387 carry is a card-shape decision rather than a data one, and it
#   is not made in a county build.
#
# THE CHAIR MARKER IS IN THE NAME CELL AND ONLY THERE, which is the trap this
# table sets. "(Chair)" appears in FOUR committee cells as well — District 5's
# Administration (Chair), 14's Health and Human Services (Chair), 15's Public
# Protection & Judiciary (Chair), 18's Transportation (Chair) — and those are
# committee chairs, not the board's. A row-level search for the word would make
# five board chairs out of one, and District 18 would collect both titles at
# once: Jerry Van Someren is the board's Vice-Chair AND chairs Transportation.
# So the role is read from the <strong> name cell alone, gated for uniqueness
# (the Calumet rule), and cross-checked against the page's OWN officer block in
# the sidebar, which names Bob Feidler (Chair) and Jerry Van Someren
# (Vice-Chair) independently of the table.
# THE NAME IS LTSB'S, NOT THE COUNTY'S. The county writes itself "St. Croix"
# on every page of its own site; the state's ward filing — which is the shipped
# geometry, and therefore the key this roster joins on — writes "St Croix" with
# no period. build_wi_county_board_roster.py gates the two as byte-identical
# and refused this county on the first build, correctly: a roster keyed on a
# name the map does not use is a roster that silently matches nothing. The
# fleet carries both spellings on purpose, each matching its own source (the
# census-derived outlines and coverage anchors say "St. Croix").
ST_CROIX_TABLE = {
    "fips": "55109", "name": "St Croix", "seats": 19,
    "source_url": "https://sccwi.gov/483/Districts-Supervisors",
    "domain": "sccwi.gov",
}
SC_ROW = re.compile(r"(?is)<tr[^>]*>(.*?)</tr>")
SC_CELL = re.compile(r"(?is)<td[^>]*>(.*?)</td>")
SC_NAME = re.compile(r"(?is)<strong>(.*?)</strong>")
# `mailto:` then OPTIONAL WHITESPACE: District 16's link is written
# "mailto: mike.barcalow@sccwi.gov", one stray space that a tighter pattern
# reads as no address at all — and an 18-of-19 e-mail count looks like a
# supervisor who publishes none rather than like a typo in the markup.
SC_MAIL = re.compile(r'(?i)mailto:\s*([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+)')
SC_PHONE = re.compile(r"(?i)\bPhone\b\s*:?\s*(\d{3})[-.\s](\d{3})[-.\s](\d{4})")
SC_ROLE = re.compile(r"(?i)\(\s*((?:Vice-?\s*)?Chair(?:person|man|woman)?)\s*\)")
# The sidebar's own officer block: "<a ...>Bob Feidler (Chair)</a>" twice over.
SC_OFFICER = re.compile(r"(?i)>\s*([A-Z][^<>()]{2,40}?)\s*\((Chair|Vice-Chair)\)\s*<")
SC_MIN_EMAILS = 17          # 19 of 19 today
SC_MIN_PHONES = 13          # 15 of 19 today; four fall to the Clerk's line
SC_MIN_WARD_PAIRS = 110     # 131 today


def _sc_flat(cell):
    """One table cell as text, its <br> line breaks kept as separators."""
    cell = re.sub(r"(?i)<br\s*/?>", " \x1e ", cell)
    cell = re.sub(r"<[^>]+>", " ", cell)
    return re.sub(r"\s+", " ", html_lib.unescape(cell).replace("\xa0", " ")).strip()


def scrape_st_croix_table(spec):
    """All seats or nothing, out of the county's own district table."""
    county, seats = spec["name"], spec["seats"]
    page = fetch(spec["source_url"])
    if "<tbody>" not in page:
        raise RuntimeError("%s: no table on %s — the page has been rebuilt; "
                           "re-read it" % (county, spec["source_url"]))
    body = page[page.index("<tbody>"):page.index("</tbody>")]
    rows = SC_ROW.findall(body)

    out, wards, munis, numbers = {}, {}, {}, {}
    for row in rows:
        cells = SC_CELL.findall(row)
        if len(cells) < 4:
            raise RuntimeError("%s: a table row carries %d cells, not 5 — the "
                               "column layout has changed and every field below "
                               "would be read out of the wrong one"
                               % (county, len(cells)))
        digits = re.sub(r"\D", "", _sc_flat(cells[0]))
        if not digits:
            raise RuntimeError("%s: a table row's first cell is %r, not a "
                               "district number" % (county, _sc_flat(cells[0])[:40]))
        district = int(digits)

        # THE NAME CELL, AND THE ROLE ONLY FROM IT — see the note above.
        head = SC_NAME.search(cells[3])
        if not head:
            raise RuntimeError("%s: district %d's contact cell has no bold name — "
                               "the table stopped marking them and the address "
                               "line below would be read as the person"
                               % (county, district))
        raw = _sc_flat(head.group(1))
        role = None
        got = SC_ROLE.search(raw)
        if got:
            role = re.sub(r"\s+", " ", got.group(1)).strip()
            raw = SC_ROLE.sub("", raw)
        name = clean(raw.replace("\x1e", " "))[0]
        if not is_name(name):
            raise RuntimeError("%s: district %d resolved the name %r — that is "
                               "not a name, and the cell has reshaped"
                               % (county, district, name))
        entry = {"name": name, "vacant": False, "role": role}

        contact = _sc_flat(cells[3])
        mail = SC_MAIL.search(cells[3])
        if mail:
            entry["email"] = mail.group(1).lower()
        numbers[district] = ["-".join(m.groups()) for m in SC_PHONE.finditer(contact)]

        wards[district], munis[district] = parse_composition(
            _sc_flat(cells[1]).replace("\x1e", ", "))
        if not munis[district]:
            raise RuntimeError("%s: district %d's ward cell names no municipality "
                               "(%r) — the composition is what witnesses the "
                               "numbering, so this cannot ship unchecked"
                               % (county, district, _sc_flat(cells[1])[:80]))
        out[district] = entry

    seen = sorted(out)
    if seen != list(range(1, seats + 1)):
        raise RuntimeError("%s: the table lists districts %s, not 1..%d — re-read "
                           "%s" % (county, seen, seats, spec["source_url"]))

    drop_shared_phones(county, numbers, out)

    names = [r["name"] for r in out.values()]
    if len(set(names)) != len(names):
        dupes = sorted({n for n in names if names.count(n) > 1})
        raise RuntimeError("%s: the same person is filed under two districts (%s)"
                           % (county, dupes))

    emails = sum(1 for r in out.values() if r.get("email"))
    phones = sum(1 for r in out.values() if r.get("phone"))
    own = sum(1 for r in out.values()
              if (r.get("email") or "").endswith("@" + spec["domain"]))
    agree = sum(1 for r in out.values() if r.get("email")
                and name_fold(r["name"].split()[-1]) in name_fold(r["email"].split("@")[0]))
    if emails < SC_MIN_EMAILS or phones < SC_MIN_PHONES:
        raise RuntimeError("%s: %d e-mails and %d phones across %d seats (floors "
                           "%d/%d) — the contact cell has reshaped and contact is "
                           "being dropped silently"
                           % (county, emails, phones, seats,
                              SC_MIN_EMAILS, SC_MIN_PHONES))
    if own != emails or agree < emails - 1:
        raise RuntimeError("%s: %d of %d mailboxes are on %s and %d agree with "
                           "their own supervisor's surname — a row has shifted"
                           % (county, own, emails, spec["domain"], agree))

    # THE PAGE'S OWN OFFICER BLOCK, INDEPENDENT OF THE TABLE.
    tail = page[page.index("</tbody>"):]
    stated = {}
    for who, what in SC_OFFICER.findall(tail):
        stated[clean(who)[0]] = what
    listed = {r["name"]: r["role"] for r in out.values() if r["role"]}
    if not stated:
        raise RuntimeError("%s: the page's officer block names nobody — it is the "
                           "only check on the table's own chair marks" % county)
    if {k: v.lower().replace("-", " ") for k, v in stated.items()} != \
       {k: v.lower().replace("-", " ") for k, v in listed.items()}:
        raise RuntimeError("%s: the table marks %s and the page's own officer "
                           "block names %s — the two disagree and neither is "
                           "guessed at" % (county, listed, stated))
    roles = [v for v in listed.values()]
    if len(set(roles)) != len(roles):
        raise RuntimeError("%s: two supervisors carry the same title (%s)"
                           % (county, sorted(listed.items())))

    print("  %-12s %d seats, %d phones, %d e-mails (no address is read: the "
          "contact column mixes the Government Center with home addresses and "
          "nothing separates them)" % (county, seats, phones, emails),
          file=sys.stderr)
    print("  witness %-12s %d/%d supervisors' names agree with their own county "
          "mailbox; officers %s confirmed by the page's own block"
          % (county, agree, seats,
             ", ".join("%s (%s)" % (k, v) for k, v in sorted(listed.items()))),
          file=sys.stderr)
    ward_number_witness(spec["fips"], county, wards, seats,
                        min_pairs=SC_MIN_WARD_PAIRS, munis=munis)
    return {str(d): r for d, r in out.items()}, spec["source_url"]


# --- Chippewa: h-cards on the board page, witnessed by the staff directory ----
#
# THE PAGE CARRIES A STALE VACANCY NOTICE ABOVE A DIRECTORY THAT CONTRADICTS IT,
# and that is the whole trap. Above the member cards, in hand-typed prose, sits
# "Seeking County Board Supervisor for District 6" — applications due 4:30 p.m.
# on Tuesday, 16 June 2026, for a term running to April 2028. Twelve cards
# further down, District 6 is Les Danielson, with a phone and a county mailbox,
# and the county's own full staff directory says the same. The seat was filled
# and the notice was never taken down. ANY READING THAT LOOKED FOR THE WORD —
# a `VACANT` sweep of the page, which is exactly what this file does for the
# counties that mark empty seats — SHIPS A TWENTY-SEAT BOARD FOR A COUNTY THAT
# SEATS TWENTY-ONE, and drops a named supervisor who is in office. So the
# vacancy test is per CARD here and never per page: prose above a directory is
# not the directory, and the CMS module is the surface the county maintains.
#
# TWO COUNTY SURFACES, AND BOTH MUST NAME THE SAME PERSON IN THE SAME DISTRICT.
# The board page's widget and the county's full staff directory
# (chippewacountywi.gov/Directory.aspx) are separate renderings, and the second
# is what settles District 6 rather than this project deciding which half of one
# page to believe. The witness is cheap — one extra fetch — and it is the check
# that would catch a widget left stale the way the notice was.
#
# THE DISTRICT COMES OUT OF EACH CARD'S OWN JOB TITLE ("District 7, Chair"),
# never out of position: the widget happens to run 1..21 in order today, and an
# adjacency reading would survive that and scramble the board the day it stops.
# The role rides the same string, after the comma.
#
# THERE IS NO WARD WITNESS FOR THIS COUNTY AND THAT IS A MEASUREMENT. Clark,
# Pierce, Marathon and St. Croix each print the municipalities and wards their
# districts are made of, which is what lets ward_number_witness() prove the
# county and the state number the same districts. Chippewa publishes 21
# per-district map PDFs and a countywide map whose only table gives each
# district's POPULATION and deviation — no composition anywhere, and LTSB's ward
# layer carries no population field to compare that table against. So Chippewa
# ships on the same footing as the 41 other board-page counties: the district
# key is the county's own statement on its own card, cross-checked against a
# second county surface, and the run log says so rather than leaving the absence
# to be inferred.
#
# THE MAILBOX IS NAME-KEYED, NOT DISTRICT-KEYED — jflater@ for James Flater —
# so unlike Door's districtN@ it witnesses the NAME rather than the district.
# It still earns its gate: a card boundary that moved would put a name against
# somebody else's mailbox on nearly every seat at once. The surname is taken
# past a generational suffix, because District 17 is "George Rohmeyer, Jr." and
# the last WORD of that is "Jr.".
CHIPPEWA_DIRECTORY = {
    "fips": "55017", "name": "Chippewa", "seats": 21,
    "source_url": "https://chippewacountywi.gov/162/County-Board-Supervisors",
    "witness_url": "https://chippewacountywi.gov/Directory.aspx",
    "domain": "chippewacountywi.gov",
}
CH_DIST = re.compile(r"(?i)^District\s*(\d{1,2})\b")
CH_MAIL = re.compile(r'(?i)mailto:\s*([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+)')
CH_PHONE = re.compile(r"\b(\d{3})[-.\s](\d{3})[-.\s](\d{4})\b")
CH_SUFFIX = re.compile(r"(?i)^(?:jr|sr|ii|iii|iv|v)\.?$")
CH_MIN_EMAILS = 19       # 21 of 21 today
CH_MIN_PHONES = 19       # 21 of 21 today


def _ch_surname(name):
    """The surname, looking past a generational suffix ("Rohmeyer, Jr.")."""
    parts = [p.strip(",") for p in name.replace(",", " ").split() if p.strip(",")]
    while len(parts) > 1 and CH_SUFFIX.match(parts[-1]):
        parts.pop()
    return parts[-1] if parts else ""


def scrape_chippewa_directory(spec):
    """All seats or nothing, from the board page's h-cards, witnessed twice."""
    county, seats = spec["name"], spec["seats"]
    page = fetch(spec["source_url"])
    out, numbers, roles = {}, {}, {}
    for m in HCARD_ITEM.finditer(page):
        body = m.group(1)
        name, title = HCARD_NAME.search(body), HCARD_TITLE.search(body)
        if not (name and title):
            continue
        who = " ".join(html_lib.unescape(_TAG.sub(" ", name.group(1))).split())
        office = " ".join(html_lib.unescape(_TAG.sub(" ", title.group(1))).split())
        stated = CH_DIST.match(office)
        if not stated:
            continue                    # a card on this page that is not a seat
        district = int(stated.group(1))
        if not (1 <= district <= seats):
            raise RuntimeError("%s: a card states district %d on a %d-seat board "
                               "— re-read %s" % (county, district, seats,
                                                 spec["source_url"]))
        if district in out:
            raise RuntimeError("%s: two cards state district %d (%r and %r)"
                               % (county, district, out[district]["name"], who))
        # THE VACANCY TEST IS PER CARD — see the note above. A page-wide sweep
        # would find the stale notice and empty a seat somebody holds.
        if VACANT.search(who):
            out[district] = {"name": None, "vacant": True, "role": None}
            continue
        if not is_name(who):
            raise RuntimeError("%s: district %d resolved %r, which does not read "
                               "as a name — re-read %s"
                               % (county, district, who, spec["source_url"]))
        row = {"name": clean(who)[0], "vacant": False, "role": None}
        mail = CH_MAIL.search(body)
        if mail:
            row["email"] = mail.group(1).lower()
        tel = HCARD_TEL.search(body)
        if tel:
            got = CH_PHONE.search(
                " ".join(html_lib.unescape(_TAG.sub(" ", tel.group(1))).split()))
            if got:
                numbers[district] = ["-".join(got.groups())]
        role = STRUCTURED_ROLE.search(office)
        if role:
            roles[district] = role_case(role.group(1))
        out[district] = row

    seen = sorted(out)
    if seen != list(range(1, seats + 1)):
        raise RuntimeError("%s: the directory states districts %s, not 1..%d — "
                           "the widget has reshaped; re-read %s"
                           % (county, seen, seats, spec["source_url"]))
    drop_shared_phones(county, numbers, out)

    named = {d: r for d, r in out.items() if not r["vacant"]}
    names = [r["name"] for r in named.values()]
    if len(set(names)) != len(names):
        dupes = sorted({n for n in names if names.count(n) > 1})
        raise RuntimeError("%s: the same person is filed under two districts (%s)"
                           % (county, dupes))
    emails = sum(1 for r in named.values() if r.get("email"))
    phones = sum(1 for r in named.values() if r.get("phone"))
    own = sum(1 for r in named.values()
              if (r.get("email") or "").endswith("@" + spec["domain"]))
    agree = sum(1 for r in named.values() if r.get("email")
                and name_fold(_ch_surname(r["name"])) in name_fold(r["email"].split("@")[0]))
    want_mail = CH_MIN_EMAILS - (seats - len(named))
    want_tel = CH_MIN_PHONES - (seats - len(named))
    if emails < want_mail or phones < want_tel:
        raise RuntimeError("%s: %d e-mails and %d phones across %d seats (floors "
                           "%d/%d) — the widget has reshaped and contact is being "
                           "dropped silently"
                           % (county, emails, phones, seats, want_mail, want_tel))
    if own != emails or agree < emails - 1:
        raise RuntimeError("%s: %d of %d mailboxes are on %s and %d agree with "
                           "their own supervisor's surname — a card boundary has "
                           "moved" % (county, own, emails, spec["domain"], agree))

    # THE SECOND COUNTY SURFACE. A fetch failure is not a disagreement.
    try:
        raw = fetch(spec["witness_url"])
    except Exception as e:              # noqa: BLE001 - the witness, never the source
        print("  WITNESS SKIPPED %-9s staff directory unreachable (%s) — the "
              "roster ships on the board page alone this run" % (county, e),
              file=sys.stderr)
    else:
        # MATCHED ON LETTERS AND DIGITS ALONE, in both directions. The two
        # surfaces punctuate the same fact differently — the directory renders
        # each field in its own tag, so flattening gives "Les Danielson | |
        # District 6", and clean() has already turned "George Rohmeyer, Jr."
        # into "George Rohmeyer Jr". Comparing the stripped forms asks the only
        # question that matters (does this name sit against this district) and
        # is not defeated by either side's markup. The trailing guard is what
        # keeps district 2 from matching district 21.
        directory = re.sub(r"[^a-z0-9]", "",
                           html_lib.unescape(_TAG.sub(" ", raw)).lower())
        missing = [(d, r["name"]) for d, r in sorted(named.items())
                   if not re.search(re.escape(name_fold(r["name"]) + "district%d" % d)
                                    + r"(?!\d)", directory)]
        if missing:
            raise RuntimeError(
                "%s: the county's own staff directory does not put %s — the "
                "board page and the staff directory disagree about who holds "
                "which seat, and neither is guessed at"
                % (county, "; ".join("%s in district %d" % (n, d)
                                     for d, n in missing)))
        print("  witness %-12s %d/%d supervisors named in the same district by "
              "the county's own staff directory" % (county, len(named), seats),
              file=sys.stderr)

    print("  %-12s %d seats, %d phones, %d e-mails; %d/%d mailboxes agree with "
          "their own surname. NO WARD WITNESS: the county publishes district "
          "maps and a population table, never a composition"
          % (county, seats, phones, emails, agree, emails), file=sys.stderr)
    rows = {str(d): r for d, r in out.items()}
    return attach_unique_roles(roles, rows, county), spec["source_url"]


# --- Menominee: a joint County/Town board, five wards and two at large --------
#
# THE SMALLEST BOARD IN THE FLEET AND THE ONLY ONE WHOSE MEMBERS ARE NOT ALL
# DISTRICTED. co.menominee.wi.us/county-board/ names all seven supervisors of
# what the county itself calls the "Menominee County and Town Board of
# Supervisors" — the county is coextensive with the Town of Menominee and the
# two share one governing body — under three headings the county writes itself:
# Chair, Vice-Chair, Board Members. Five hold a WARD; two are elected AT LARGE,
# and one of those two is the Vice-Chair.
#
# THE WARD IS THE SUPERVISORY DISTRICT HERE, AND THE STATE SAYS SO OUTRIGHT.
# LTSB files Menominee with exactly five wards and maps each to the
# same-numbered SUPERID — ward 0001 to district 01, straight through to 5 — so
# the county's "Ward #3" IS district 3, proven by the state's own filing rather
# than inferred from a name. That is the ward witness in its strongest possible
# form and it is why this county can ship at all: nothing else on the page uses
# the word district.
#
# THE TWO AT-LARGE SUPERVISORS ARE NOT DROPPED. They hold no district, so they
# cannot key into a district-keyed roster — and leaving them out would ship a
# five-member board for a county that seats seven, with the Vice-Chair among the
# missing. That is the Alexander (Illinois) lesson: a card that names fewer
# people than the body seats must say so rather than let the absence read as
# completeness. They ride a county-keyed entry ("<fips>-at-large") in the same
# roster file, and every district card in the county names them beneath its own
# supervisor, because a reader in ward 3 is represented by all three.
#
# EACH MEMBER'S OWN PAGE IS FETCHED AND IT WITNESSES TWO THINGS. It prints
# "Name: Ben Warrington" — the given-name-first form, which confirms the flip
# out of the list page's "Warrington,  Ben" (two spaces, and suffixes ride the
# surname: "Cox Sr.,  Douglas") — and "Ward: #3", which confirms the ward the
# list page filed them under. Seven pages, and the same list-versus-own-page
# agreement Marathon and Oconto already rely on.
#
# NO CONTACT SHIPS, AND THAT IS THE CALUMET RULE RATHER THAN AN OMISSION. The
# only way to reach a supervisor through this site is a per-member contact FORM;
# there is no mailbox and no phone anywhere on either page. A form is not an
# address, so nothing is shipped as one and the member page is not offered as a
# "Supervisor page" either. The card's footer link is the board page, where the
# form is one click away and labelled as what it is.
MENOMINEE_BOARD = {
    "fips": "55078", "name": "Menominee", "seats": 5, "at_large": 2,
    "source_url": "https://www.co.menominee.wi.us/county-board/",
}
# "<b>Chair</b>" / "<b>Vice-Chair</b>" / "<b>Board Members</b>" — the county's
# own headings, each followed by the block of members holding that office.
MN_HEAD = re.compile(r"(?is)<b>\s*(Chair|Vice-Chair|Board Members)\s*</b>")
# "<a href='...&i=HASH'>Warrington,  Ben</a> - Ward #3"
MN_ROW = re.compile(
    r'(?is)<a href="(?P<url>[^"]*\bi=[0-9a-f]+)">(?P<name>[^<]+)</a>\s*-\s*'
    r'Ward\s*(?P<ward>#\s*\d+|At\s+Large)')
MN_OWN_NAME = re.compile(r"(?is)\bName:\s*\|?\s*([A-Z][^|<]{1,60}?)\s*\|")
MN_OWN_WARD = re.compile(r"(?is)\bWard:\s*\|?\s*(#\s*\d+|At\s+Large)\b")


def surname_first(county, raw):
    """"Warrington,  Ben" -> "Ben Warrington"; "Cox Sr.,  Douglas" -> "Douglas Cox Sr.".

    THE FLIP IS `clean()`'s, NOT THIS FUNCTION'S. Its comma branch already
    swaps a surname-first pair and keeps a suffix where it belongs, and doing
    the split here first meant handing it an already-flipped string whose
    trailing "Sr." then read as stray punctuation. What is left here is the
    SHAPE CHECK: the comma has to be there, because a page that stops using it
    would send every name through unflipped and backwards without a word.
    """
    raw = " ".join(html_lib.unescape(raw).split())
    if "," not in raw:
        raise RuntimeError("%s: the name %r is not 'Surname, Given' — the page "
                           "has changed how it writes names and every name would "
                           "ship backwards" % (county, raw))
    return clean(raw)[0]


def dmi_flat(html):
    """One page of this CMS as pipe-separated text, for its `Label:` fields.

    SHARED BY MENOMINEE AND LANGLADE, which run the same vendor CMS: `<b>Role</b>`
    headings over `.colab` blocks of "Surname,  Given" links, and a per-member
    page whose facts sit in `Label: | value |` rows.

    UNESCAPE BEFORE COLLAPSING WHITESPACE, not after. This page puts a spacer
    cell between every label and its value, written `&#160;` — still an entity
    while `\s+` runs, so collapsing first leaves `Name: | \xa0 | Ben
    Warrington` and the pipe-run rule never fires. The label then matched
    nothing here and found the CONTACT FORM's "Name:" further down instead,
    which is a different field on a different subject.
    """
    body = re.sub(r"(?is)<(script|style).*?</\1>", " ", html)
    body = re.sub(r"\s+", " ", html_lib.unescape(re.sub(r"<[^>]+>", " | ", body)))
    return re.sub(r"(\| )+", "| ", body)


def scrape_menominee_board(spec):
    """All seven or nothing: five ward seats keyed as districts, two at large."""
    county, seats = spec["name"], spec["seats"]
    page = fetch(spec["source_url"])
    heads = [(m.start(), m.group(1)) for m in MN_HEAD.finditer(page)]
    if len(heads) != 3:
        raise RuntimeError("%s: the page carries %d of its three office headings "
                           "(Chair, Vice-Chair, Board Members) — it has been "
                           "rebuilt; re-read %s"
                           % (county, len(heads), spec["source_url"]))
    members = []
    for n, (start, office) in enumerate(heads):
        end = heads[n + 1][0] if n + 1 < len(heads) else len(page)
        for m in MN_ROW.finditer(page[start:end]):
            ward = re.sub(r"\s+", "", m.group("ward")).lower()
            members.append({
                "name": surname_first(county, m.group("name")),
                "ward": None if ward == "atlarge" else int(ward.lstrip("#")),
                "role": None if office == "Board Members" else office,
                "url": urllib.parse.urljoin(spec["source_url"],
                                            html_lib.unescape(m.group("url"))),
            })

    districted = sorted(x["ward"] for x in members if x["ward"] is not None)
    at_large = [x for x in members if x["ward"] is None]
    if districted != list(range(1, seats + 1)):
        raise RuntimeError("%s: the page names wards %s, not 1..%d — the board's "
                           "composition has changed; re-read %s and LTSB's ward "
                           "filing together" % (county, districted, seats,
                                                spec["source_url"]))
    if len(at_large) != spec["at_large"]:
        raise RuntimeError("%s: the page names %d at-large supervisor(s), not %d — "
                           "the board's composition has changed and the card's "
                           "own statement of its size would be wrong"
                           % (county, len(at_large), spec["at_large"]))
    names = [x["name"] for x in members]
    if len(set(names)) != len(names):
        raise RuntimeError("%s: the same person is named twice (%s)"
                           % (county, sorted({n for n in names if names.count(n) > 1})))

    # EACH MEMBER'S OWN PAGE, AS A WITNESS ONLY — see the note above. A fetch
    # failure is not a disagreement, but a page that names someone else is.
    checked = 0
    for n, member in enumerate(members):
        if n:
            time.sleep(0.4)             # seven pages of somebody else's server
        try:
            own = dmi_flat(fetch(member["url"]))
        except Exception as e:          # noqa: BLE001 - the witness, never the source
            print("  note %-12s %s's own page unreachable (%s) — unwitnessed this "
                  "run" % (county, member["name"], e), file=sys.stderr)
            continue
        said_name, said_ward = MN_OWN_NAME.search(own), MN_OWN_WARD.search(own)
        if not (said_name and said_ward):
            raise RuntimeError("%s: %s's own page states no Name/Ward pair — the "
                               "member pages have reshaped and the list page's "
                               "ward would be unwitnessed (%s)"
                               % (county, member["name"], member["url"]))
        if name_fold(said_name.group(1)) != name_fold(member["name"]):
            raise RuntimeError("%s: the list files %r where their own page says "
                               "%r — the two county surfaces disagree about who "
                               "this is" % (county, member["name"],
                                            said_name.group(1).strip()))
        ward = re.sub(r"\s+", "", said_ward.group(1)).lower()
        mine = None if ward == "atlarge" else int(ward.lstrip("#"))
        if mine != member["ward"]:
            raise RuntimeError("%s: the list files %s under ward %s and their own "
                               "page says %s — the two county surfaces disagree "
                               "about which seat this is"
                               % (county, member["name"], member["ward"], mine))
        checked += 1

    out = {}
    for member in members:
        if member["ward"] is None:
            continue
        out[str(member["ward"])] = {"name": member["name"], "vacant": False,
                                    "role": member["role"]}
    print("  %-12s %d ward seats + %d at large, no contact (the county's only "
          "channel is a per-member contact FORM, which is not an address)"
          % (county, seats, len(at_large)), file=sys.stderr)
    print("  witness %-12s %d/%d supervisors' own pages confirm their name and "
          "ward; LTSB files ward N as district N for all %d"
          % (county, checked, len(members), seats), file=sys.stderr)
    for member in at_large:
        print("  at-large %-9s %s%s" % (county, member["name"],
                                        " (%s)" % member["role"] if member["role"] else ""),
              file=sys.stderr)
    return out, [{"name": x["name"], "role": x["role"]} for x in at_large], \
        spec["source_url"]


def municipality_name_witness(fips, county, texts, seats):
    """The county's own composition PROSE against LTSB's municipality filing.

    THE NAME-SET CHECK, FOR COUNTIES WHOSE COMPOSITION IS NOT PARSEABLE AS
    WARDS. ward_number_witness() is stronger and is used wherever a county
    writes its wards in a shape parse_composition() can read. Langlade does
    not: its nine city districts read "First Ward- Antigo" with the ward as an
    ORDINAL WORD and no type; its town districts read "Towns of Ainsworth,
    Elcho Ward 2, Langlade Ward 2, Price W2", where one list carries three
    different ward notations and the unnumbered towns mean ward 1 by
    implication. Every rule needed to parse that is a guess about intent.
    What is NOT a guess is which PLACES a district covers, and that is the
    thing that moves if two publishers number their districts differently.

    So this asks only: does the set of municipality names the county names in
    district N equal the set LTSB files in district N? Substring matching over
    LTSB's own name list, which is why the containment guard below is a gate
    rather than a comment — a county with both "York" and "New York" would
    score a false agreement, and the check has to refuse rather than mislead.

    A FETCH FAILURE IS NOT A DISAGREEMENT: an unreachable witness says nothing
    about the roster and stands aside; a witness that RUNS and disagrees fails
    the county, because then the district KEY is what is in doubt.
    """
    try:
        data = _fetch_json(
            LTSB_WARD_QUERY + "?where=CNTY_FIPS%%3D%%27%s%%27&outFields="
            "MCD_NAME,SUPERID&returnGeometry=false&f=json" % fips)
        feats = data.get("features") or []
        if not feats:
            raise RuntimeError("no wards returned")
    except Exception as e:          # noqa: BLE001 - the witness, never the source
        print("  WITNESS SKIPPED %-9s LTSB ward layer unreachable (%s) — the "
              "roster ships unwitnessed this run" % (county, e), file=sys.stderr)
        return
    ltsb = {}
    for f in feats:
        a = f.get("attributes") or {}
        ltsb.setdefault(int(a["SUPERID"]), set()).add(_jk_norm(str(a.get("MCD_NAME", ""))))
    names = sorted({n for v in ltsb.values() for n in v})
    nested = sorted("%s in %s" % (a, c) for a in names for c in names
                    if a != c and a and a in c)
    if nested:
        print("  WITNESS SKIPPED %-9s one municipality name contains another "
              "(%s) — substring matching would score a false agreement"
              % (county, ", ".join(nested[:3])), file=sys.stderr)
        return

    agree, wrong = 0, []
    for district in sorted(texts):
        text = _jk_norm(texts[district])
        said = {n for n in names if n in text}
        want = ltsb.get(district, set())
        if said == want:
            agree += 1
        else:
            wrong.append((district, sorted(said), sorted(want)))
    if wrong:
        raise RuntimeError(
            "%s: the county and LTSB disagree about which municipalities are in "
            "%d district(s) — %s. The district NUMBERS are what is in doubt, so "
            "nothing ships unchecked"
            % (county, len(wrong), "; ".join(
                "D%d county=%s state=%s" % (d, s, w) for d, s, w in wrong[:3])))
    print("  witness %-12s %d/%d districts name exactly the municipalities LTSB "
          "files there" % (county, agree, seats), file=sys.stderr)


# --- Langlade: the same CMS as Menominee, with contact on the member pages ----
#
# ITS BOARD PAGE NAMES ALL 21 SUPERVISORS WITH THEIR DISTRICTS AND THE PLACES
# EACH DISTRICT COVERS, and has all along. co.langlade.wi.us runs the same
# vendor CMS as Menominee — `<b>Role</b>` headings over `.colab` blocks of
# "Surname,  Given" links to per-member `?i=<hash>` pages — so the list reader
# and `dmi_flat` are shared. What differs is what the member pages carry:
# Menominee's offer only a contact form, Langlade's print the district again,
# a phone, and for most a DISTRICT-KEYED county mailbox.
#
# THE MAILBOX IS THE DOOR WITNESS, and 16 of the 21 have one: district7@
# co.langlade.wi.us on district 7's page, straight through. Every one that
# exists must match the district whose row it sits under, which is the check
# that would catch a block boundary moving. The other five publish no address
# at all and ship without one rather than with somebody else's.
#
# EVERY MEMBER PAGE PRINTS A HOME ADDRESS — all 21, from "1116 Clermont Street"
# to "N7299 Kennedy Road" — and none is read. That is the standing rule rather
# than a decision about this county.
#
# THE COMPOSITION IS WITNESSED BY NAME, NOT BY WARD, and the reason is in
# municipality_name_witness() above: this county writes ordinal ward words for
# its city districts and three different ward notations inside one town list.
# All 21 districts name exactly the municipalities LTSB files there.
#
# TWO SUPERVISORS SIT UNDER ONE "Vice-Chair" HEADING — district 4 and district
# 9 — and the page carries nothing to say which holds it or whether the county
# seats two. That is Calumet's case exactly, so attach_unique_roles() prints
# the ambiguity and ships the title on NEITHER; the Chairperson is unambiguous
# and ships. Naming a vice-chair here would mean picking one of two people at
# random and printing an office beside their name.
#
# THE BLUE BOOK'S CHAIR FOR THIS COUNTY IS SOMEBODY WHO IS NOT ON THE BOARD.
# It records Ben Pierce (April 2025); the county's own page names Steve Maier
# of district 21, and no Pierce appears among the 21. Boards elect their chair
# each April organizational meeting, so this is turnover rather than a
# contradiction — and build_wi_county_officer_roster.py already reconciles the
# two, with the county's own page superseding the book. Nothing here does
# anything about it beyond shipping what the county publishes.
LANGLADE_BOARD = {
    "fips": "55067", "name": "Langlade", "seats": 21,
    "source_url": "https://www.co.langlade.wi.us/government/board_and_committees/",
    "origin": "https://www.co.langlade.wi.us",
    "domain": "co.langlade.wi.us",
}
DMI_HEAD = re.compile(r"(?is)<b>\s*(Chairperson|Vice-Chair|Board Members)\s*</b>")
# THE ANCHOR CARRIES ATTRIBUTES ON SOME OF THIS VENDOR'S SITES AND NONE ON
# OTHERS: Langlade writes <a href="...">, Florence writes
# <a href="..." class="bold-link">. The tightened form matched zero of
# Florence's twelve rows and would have read as "this county publishes no
# board list" rather than as a regex one attribute too strict.
DMI_ROW = re.compile(
    r'(?is)<a\s+href="(?P<url>[^"]*\bi=[0-9a-f]+)"[^>]*>(?P<name>[^<]+)</a>\s*-\s*'
    r'District\s*#\s*(?P<district>\d{1,2})\s*-?\s*(?P<composition>[^<]*)')
DMI_OWN_NAME = re.compile(r"(?is)\bName:\s*\|?\s*([^|<]{2,60}?)\s*\|")
DMI_OWN_DIST = re.compile(r"(?is)\bDistrict\s*#:\s*\|?\s*(\d{1,2})\b")
DMI_PHONE = re.compile(r"(?is)\bPhone Number:\s*\|?\s*(\d{3})[-.\s](\d{3})[-.\s](\d{4})\b")
DMI_MAIL = re.compile(r"(?is)\bEmail Address:\s*\|?\s*([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+)")
LG_MIN_PHONES = 18      # 21 of 21 today
LG_MIN_EMAILS = 13      # 16 of 21 today; five supervisors publish none


def scrape_langlade_board(spec):
    """All seats or nothing, witnessed by each member's own page and mailbox."""
    county, seats = spec["name"], spec["seats"]
    page = fetch(spec["source_url"])
    heads = [(m.start(), m.group(1)) for m in DMI_HEAD.finditer(page)]
    if len(heads) != 3:
        raise RuntimeError("%s: the page carries %d of its three office headings "
                           "(Chairperson, Vice-Chair, Board Members) — it has "
                           "been rebuilt; re-read %s"
                           % (county, len(heads), spec["source_url"]))
    out, roles, texts, links = {}, {}, {}, {}
    for n, (start, office) in enumerate(heads):
        end = heads[n + 1][0] if n + 1 < len(heads) else len(page)
        for m in DMI_ROW.finditer(page[start:end]):
            district = int(m.group("district"))
            if district in out:
                raise RuntimeError("%s: two rows state district %d (%r and %r)"
                                   % (county, district, out[district]["name"],
                                      m.group("name")))
            name = surname_first(county, m.group("name"))
            if not is_name(name):
                raise RuntimeError("%s: district %d resolved the name %r, which "
                                   "does not read as a name — re-read %s"
                                   % (county, district, name, spec["source_url"]))
            out[district] = {"name": name, "vacant": False, "role": None}
            texts[district] = html_lib.unescape(m.group("composition"))
            links[district] = urllib.parse.urljoin(
                spec["source_url"], html_lib.unescape(m.group("url")))
            if office != "Board Members":
                roles[district] = office

    seen = sorted(out)
    if seen != list(range(1, seats + 1)):
        raise RuntimeError("%s: the page lists districts %s, not 1..%d — the "
                           "board's composition has changed; re-read %s"
                           % (county, seen, seats, spec["source_url"]))
    names = [r["name"] for r in out.values()]
    if len(set(names)) != len(names):
        raise RuntimeError("%s: the same person is filed under two districts (%s)"
                           % (county, sorted({n for n in names if names.count(n) > 1})))

    # EACH MEMBER'S OWN PAGE: the district again, the contact, and never the
    # address it prints beside them.
    phones = emails = 0
    for n, district in enumerate(sorted(out)):
        if n:
            time.sleep(0.4)             # 21 pages of somebody else's server
        own = dmi_flat(fetch(links[district]))
        said_name, said_dist = DMI_OWN_NAME.search(own), DMI_OWN_DIST.search(own)
        if not (said_name and said_dist):
            raise RuntimeError("%s: %s's own page states no Name/District pair — "
                               "the member pages have reshaped and the list's "
                               "district would be unwitnessed (%s)"
                               % (county, out[district]["name"], links[district]))
        if name_fold(said_name.group(1)) != name_fold(out[district]["name"]):
            raise RuntimeError("%s: the list files %r where their own page says "
                               "%r — the two county surfaces disagree about who "
                               "this is" % (county, out[district]["name"],
                                            said_name.group(1).strip()))
        if int(said_dist.group(1)) != district:
            raise RuntimeError("%s: the list files %s under district %d and their "
                               "own page says %s — the two county surfaces "
                               "disagree about which seat this is"
                               % (county, out[district]["name"], district,
                                  said_dist.group(1)))
        tel = DMI_PHONE.search(own)
        if tel:
            out[district]["phone"] = "-".join(tel.groups())
            phones += 1
        mail = DMI_MAIL.search(own)
        if mail:
            # THE DISTRICT-KEYED MAILBOX MUST NAME ITS OWN DISTRICT.
            want = "district%d@%s" % (district, spec["domain"])
            if mail.group(1).lower() != want:
                raise RuntimeError(
                    "%s: district %d's page carries the mailbox %r rather than "
                    "%r — the county's own district-keyed address disagrees with "
                    "the row it sits under"
                    % (county, district, mail.group(1), want))
            out[district]["email"] = mail.group(1).lower()
            emails += 1

    if phones < LG_MIN_PHONES or emails < LG_MIN_EMAILS:
        raise RuntimeError("%s: %d phones and %d e-mails across %d seats (floors "
                           "%d/%d) — the member pages have reshaped and contact "
                           "is being dropped silently"
                           % (county, phones, emails, seats,
                              LG_MIN_PHONES, LG_MIN_EMAILS))
    print("  %-12s %d seats, %d phones, %d e-mails (%d supervisors publish no "
          "address; no home address is read, and all 21 pages print one)"
          % (county, seats, phones, emails, seats - emails), file=sys.stderr)
    print("  witness %-12s %d/%d supervisors' own pages confirm their name and "
          "district; %d/%d mailboxes are the county's own district-keyed address"
          % (county, seats, seats, emails, emails), file=sys.stderr)
    municipality_name_witness(spec["fips"], county, texts, seats)
    rows = {str(d): r for d, r in out.items()}
    return attach_unique_roles(roles, rows, county), spec["source_url"]


# --- Iron: the county I called measured-shut without opening a member's page --
#
# THE RECORD THAT SAID THIS COUNTY PUBLISHES NO DISTRICTS WAS MINE, AND IT WAS
# WRONG THE WAY EVERY OTHER RECORD THIS FILE CORRECTS WAS WRONG. /190/County-
# Board names all fifteen supervisors with their roles and no districts, and
# the county's aggregate /directory.aspx — 832 KB, 213 mailboxes — contains the
# word "district" not once. Both readings were accurate and both were about
# PAGES. Every member's OWN employee page states "District: 4" and
# "Township/Wards: 4 - Hurley Ward 4", and the board page LINKS all fourteen of
# them, in the very anchors their names were read out of. Sawyer, on this same
# CivicPlus template, had its employee pages enumerated an hour earlier.
# AN AGGREGATE THAT OMITS A FIELD IS NOT A COUNTY THAT OMITS IT.
#
# The other half of that record was a real measurement and stays true: the
# county's only district-keyed DOCUMENT is a pre-election candidate list whose
# incumbent column names nine people no longer on the board. It was the right
# thing to refuse; it was not the only thing to look at.
#
# THE DISTRICT IS STATED TWO WAYS AND ONE OF THEM IS THE ONLY WAY FOR TWO SEATS.
# Twelve pages carry a `District:` field. Kessler's and McNutt's do not — their
# number leads the `Township/Wards:` line instead ("15 - Sherman", "11 - Mercer
# Ward 1"), so a reader that takes only the labelled field ships a thirteen-seat
# board. Where both appear they must agree.
#
# THE VACANCY IS ARITHMETIC, AND IT IS GATED RATHER THAN INFERRED. The board
# page carries exactly one "VACANT, Member" row with no member page behind it,
# so no page states the empty seat's number. Fourteen districts come off the
# member pages; LTSB files fifteen; the remainder is district 3. That is only
# safe while BOTH counts hold, so the builder refuses unless the page shows
# exactly one vacancy AND exactly one district in 1..seats is unaccounted for —
# otherwise a member the directory merely dropped would be published as an
# empty seat, which tells that district it has nobody when it has someone.
#
# THE WARD COMPOSITION COMES FREE and is what witnesses the numbering. It uses
# an em-dash on some pages and a hyphen on others, and names its towns BARE and
# slash-separated ("9 — Anderson / Knight / Pence"), so the type is supplied by
# LTSB's own filing the way Forest's is — see settle() in ward_number_witness().
IRON_BOARD = {
    "fips": "55051", "name": "Iron", "seats": 15,
    "source_url": "https://www.co.iron.wi.gov/190/County-Board",
    "member_url": "https://www.co.iron.wi.gov/m/directory/employee?eid=%s",
    "domain": "ironcountywi.org",
}
IR_LINK = re.compile(r'(?is)<a[^>]+href="[^"]*[Ee][Ii][Dd]=(\d+)"[^>]*>(.*?)</a>')
IR_MEMBER = re.compile(r"(?i)^\s*(.+?)\s*,\s*((?:County Board )?(?:Vice )?Chair(?:man|person)?|Member)\s*$")
# THE COLON IS OPTIONAL AND THE PAGES DISAGREE ABOUT IT. Youngs's reads
# "District: 4" and "Township/Wards: 4 - Hurley Ward 4"; Hanson's reads
# "District 9" and "Township/Wards 9 &mdash; Anderson / Knight / Pence". A
# pattern requiring the colon failed that page outright — which is the right
# failure (the county is refused rather than shipped short) and still the wrong
# pattern. The number each label introduces is cross-checked against the other
# wherever both appear, which is what guards the looser match.
IR_DISTRICT = re.compile(r"(?i)\bDistrict\s*:?\s*(\d{1,2})\b")
IR_WARDS = re.compile(r"(?i)\bTownship\s*/\s*Wards\s*:?\s*(\d{1,2})\s*[-–—]\s*([^\n]{1,90})")
IR_MAIL = re.compile(r"(?i)mailto:\s*([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+)")
IR_PHONE = re.compile(r"(?<!\d)(\d{3})[-.\s](\d{3})[-.\s](\d{4})(?!\d)")
IR_MIN_EMAILS = 12          # 14 of 14 today
IR_MIN_PHONES = 10          # 12 of 14 today
IR_MIN_WARD_PAIRS = 8       # 10 today: five districts are whole towns with no
                            # ward number ("7 - Kimball", "15 - Sherman"), which
                            # is a complete statement carrying no pair. Measured,
                            # not guessed — Barron's floor taught that.


def _ir_flat(page):
    t = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", page)
    t = re.sub(r"(?i)<br\s*/?>|</(p|div|li|h[1-6])>", "\n", t)
    return html_lib.unescape(re.sub(r"<[^>]+>", " ", t)).replace("\xa0", " ")


IR_PART = re.compile(r"(?i)^(.+?)(?:\s+Wards?\s*(\d{1,2}))?$")


def _ir_composition(text):
    """({(None, name, ward)}, {(None, name)}) for one Township/Wards line.

    NOT parse_composition(), for Forest's reason: that function anchors on a
    "Town of" / "City of" / "Village of" run and Iron names its towns BARE and
    slash-separated — "Anderson / Knight / Pence", "Hurley Ward 4", "Kimball".
    Fed to it, every line yields nothing at all, which reads as a county that
    has stopped printing its composition rather than one that never wrote the
    type word. The type is left None so ward_number_witness()'s settle() takes
    it from LTSB's own filing, and a name the state files under two types stays
    unresolved and fails rather than being guessed.
    """
    pairs, munis = set(), set()
    for part in re.split(r"\s*[/,]\s*", text):
        got = IR_PART.match(part.strip())
        if not got:
            continue
        name = _jk_norm(got.group(1))
        if not name:
            continue
        munis.add((None, name))
        if got.group(2):
            pairs.add((None, name, int(got.group(2))))
    return pairs, munis


def scrape_iron_board(spec):
    """All 15 seats or nothing, out of each member's own employee page."""
    county, seats = spec["name"], spec["seats"]
    page = fetch(spec["source_url"])

    # THE BOARD PAGE: who sits, their office, and their member-page link.
    listed, vacancies = {}, 0
    for line in (x.strip() for x in _ir_flat(page).split("\n")):
        got = IR_MEMBER.match(line)
        if got and VACANT.search(got.group(1)):
            vacancies += 1
    ids = []
    for eid, raw in IR_LINK.findall(page):
        who = re.sub(r"\s+", " ", html_lib.unescape(re.sub(r"<[^>]+>", " ", raw))).strip()
        if who and eid not in [e for e, _ in ids]:
            ids.append((eid, who))
    if not ids:
        raise RuntimeError("%s: the board page links no member pages — it has been "
                           "rebuilt; re-read %s" % (county, spec["source_url"]))
    roles = {}
    for line in (x.strip() for x in _ir_flat(page).split("\n")):
        got = IR_MEMBER.match(line)
        if got and not VACANT.search(got.group(1)):
            office = re.sub(r"(?i)^county board\s+", "", got.group(2)).strip()
            if office.lower() != "member":
                listed[name_fold(clean(got.group(1))[0])] = office.title()

    out, wards, munis, numbers = {}, {}, {}, {}
    for n, (eid, who) in enumerate(ids):
        if n:
            time.sleep(0.4)             # 14 pages of somebody else's server
        own = fetch(spec["member_url"] % eid)
        flat = _ir_flat(own)
        said = IR_DISTRICT.search(flat)
        comp = IR_WARDS.search(flat)
        if not (said or comp):
            raise RuntimeError("%s: %s's page states neither a District nor a "
                               "Township/Wards line — the member pages have "
                               "reshaped and the district would be unknown (%s)"
                               % (county, who, spec["member_url"] % eid))
        # BOTH STATEMENTS WHERE BOTH EXIST — see the note above.
        if said and comp and int(said.group(1)) != int(comp.group(1)):
            raise RuntimeError("%s: %s's page says District %s and its "
                               "Township/Wards line leads %s — the page's own two "
                               "statements disagree"
                               % (county, who, said.group(1), comp.group(1)))
        district = int((said or comp).group(1))
        if district in out:
            raise RuntimeError("%s: two members claim district %d (%s and %s)"
                               % (county, district, out[district]["name"], who))
        if not (1 <= district <= seats):
            raise RuntimeError("%s: %s's page states district %d, outside 1..%d"
                               % (county, who, district, seats))
        name = clean(who)[0]
        if not _reads_as_name(name):
            raise RuntimeError("%s: district %d resolved the name %r, which does "
                               "not read as a name" % (county, district, name))
        entry = {"name": name, "vacant": False,
                 "role": listed.get(name_fold(name))}
        mail = IR_MAIL.search(own)
        if mail:
            entry["email"] = mail.group(1).lower()
        tel = IR_PHONE.search(flat)
        if tel:
            numbers[district] = ["-".join(tel.groups())]
        out[district] = entry
        if comp:
            wards[district], munis[district] = _ir_composition(comp.group(2))

    # THE EMPTY SEAT, BY ARITHMETIC THAT MUST CLOSE — see the note above.
    missing = [d for d in range(1, seats + 1) if d not in out]
    if len(missing) != vacancies:
        raise RuntimeError(
            "%s: %d district(s) have no member page (%s) and the board page shows "
            "%d vacancy row(s) — those must match, or a supervisor the directory "
            "merely dropped would ship as an empty seat"
            % (county, len(missing), ", ".join(str(d) for d in missing), vacancies))
    for d in missing:
        out[d] = {"name": None, "vacant": True, "role": None}

    seen = sorted(out)
    if seen != list(range(1, seats + 1)):
        raise RuntimeError("%s: resolved districts %s, not 1..%d"
                           % (county, seen, seats))
    drop_shared_phones(county, numbers, out)
    live = [d for d, r in out.items() if not r["vacant"]]
    names = [out[d]["name"] for d in live]
    if len(set(names)) != len(names):
        raise RuntimeError("%s: the same person is filed under two districts (%s)"
                           % (county, sorted({n for n in names if names.count(n) > 1})))
    emails = sum(1 for d in live if out[d].get("email"))
    phones = sum(1 for d in live if out[d].get("phone"))
    own_dom = sum(1 for d in live
                  if (out[d].get("email") or "").endswith("@" + spec["domain"]))
    if emails < IR_MIN_EMAILS or phones < IR_MIN_PHONES:
        raise RuntimeError("%s: %d e-mails and %d phones across %d filled seats "
                           "(floors %d/%d) — the member pages have reshaped and "
                           "contact is being dropped silently"
                           % (county, emails, phones, len(live),
                              IR_MIN_EMAILS, IR_MIN_PHONES))
    if own_dom != emails:
        raise RuntimeError("%s: %d of %d mailboxes are on %s — a page has shifted"
                           % (county, own_dom, emails, spec["domain"]))
    print("  %-12s %d seats, %d filled, %d phones, %d e-mails (the district is on "
          "each member's OWN page; the board page and the county's aggregate "
          "directory both state none)"
          % (county, seats, len(live), phones, emails), file=sys.stderr)
    if missing:
        print("  note %-12s district %s is the county's one VACANT row, identified "
              "by elimination and gated on the two counts agreeing"
              % (county, ", ".join(str(d) for d in missing)), file=sys.stderr)
    if wards:
        ward_number_witness(spec["fips"], county, wards, seats,
                            min_pairs=IR_MIN_WARD_PAIRS, munis=munis)
    return {str(d): r for d, r in out.items()}, spec["source_url"]


# --- Ashland: read once, then STOPPED by the county's own robots.txt ---------
#
# THE CRAWL STOPS AND THE NAMES STAY — the seventh county on that footing, after
# Jackson, Richland, Rusk, Polk, Dunn and Pepin. ashlandcountywi.gov publishes
#
#     User-agent: *
#     Disallow: /
#
# naming half a dozen search engines above it with narrow /admin/ and /manager/
# rules; this project's clients are none of them, so the whole site is
# disallowed to it. wi/scripts/validate_robots.py caught that on the run that
# would have added this county to the weekly schedule — the reader below had
# already been written and had already resolved all 21 seats — so what ships is
# the roster AS READ on 2026-09-02, in DOCUMENT_ROSTERS, never re-fetched, with
# its card saying the county ASKED rather than refused. robots.txt governs
# RETRIEVAL, not what already-public information may be shown, and stopping the
# fetch is exactly what the file asks for. THE READER IS KEPT rather than
# deleted: it is what the county's own say-so would re-enable, and it carries
# the two traps below, which are about the page rather than the schedule.
# Nothing here will quietly rename a client to get past a file that says no.
#
# ashlandcountywi.gov/bos gives each of the 21 districts a <p>: a <strong>
# header reading "DISTRICT n: <composition> (District n Map)", then the
# supervisor, their home address, "Phone: ..." and "Email: ...".
#
# THE COMPOSITION CARRIES A SECOND KIND OF DISTRICT AND IT MUST BE CUT FIRST.
# The header reads "City of Ashland - Wards 1 & 2 - Aldermanic 1": the city's
# ALDERMANIC districts, which are a different fabric from the county's wards
# and are none of this layer's business. Fed to parse_composition() whole, the
# trailing "- Aldermanic 1" is absorbed into the municipality NAME and the
# district resolves as the city of "ashlandaldermanic" — a municipality that
# exists nowhere, so every pair misses and the county is refused for a reason
# that has nothing to do with its numbering. The annotation is cut at the
# separator before the word.
#
# THE HEADER'S OWN MAP LINK IS ALSO INSIDE THE <strong>, so "(District n Map)"
# comes out of the same string and is removed with it.
#
# "Phone: Confidential" IS A PUBLISHED REFUSAL, NOT A NUMBER. District 1 says
# it; that supervisor ships with no phone rather than with the word.
#
# ONE WARD IS FILED DIFFERENTLY BY THE TWO PUBLISHERS AND THE SEAT STILL SHIPS.
# The county's District 11 reads "City of Ashland - Wards 18, 19 & 20"; LTSB
# files ward 18 in District 8 (with ward 21) and District 11 as wards 19 and 20.
# Twenty-nine of the thirty wards this page names land in LTSB's same-numbered
# district; that one does not. LINCOLN'S RULE DOES NOT REACH IT AND THE
# DIFFERENCE IS MEASURED, NOT ASSUMED: Lincoln withheld a seat because the
# county assigned a MAJORITY of that district's ground elsewhere (its own map
# agreed with only 48% of it). Ward 18 is 3.8% of District 8 by area — ward 21
# is the other 96.2% — so withholding District 8 would deny a correct name to
# almost everyone in it in order to handle one small city ward. What a reader
# standing in ward 18 sees is District 8 and District 8's supervisor, because
# the card reads their district from LTSB's geometry, and the county would say
# District 11. That is recorded here and in the gap record rather than smoothed
# away, and neither publisher is preferred: nothing here decides which is right.
#
# EVERY SUPERVISOR'S HOME ADDRESS IS ON THIS PAGE AND NONE IS READ.
ASHLAND_BOARD = {
    "fips": "55003", "name": "Ashland", "seats": 21,
    "source_url": "https://ashlandcountywi.gov/bos",
    "domain": "ashlandcountywi.gov",
}
# THE HEADER TAG CARRIES ATTRIBUTES ON ONE BLOCK OF TWENTY-ONE. District 14's
# is <strong style="font-size: 12pt;"> where the other twenty are bare, so a
# pattern requiring a bare tag reads this page as a twenty-seat board and the
# seat-set gate refuses the county — for a style attribute on one paragraph.
AS_BLOCK = re.compile(
    r"(?is)<strong[^>]*>\s*District\s*(\d{1,2})\s*:(.*?)</strong>"
    r"(.*?)(?=<strong[^>]*>\s*District\s*\d|\Z)")
AS_ALDER = re.compile(r"(?i)\s*[-–—]\s*Aldermanic\b.*$")
AS_MAPLINK = re.compile(r"(?is)\(\s*<a[^>]*>.*?</a>\s*\)|\(\s*District\s*\d+\s*Map\s*\)")
AS_MAIL = re.compile(r"(?i)mailto:\s*([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+)")
AS_PHONE = re.compile(r"(?i)Phone\s*:?\s*\(?(\d{3})\)?[-.\s]?(\d{3})[-.\s](\d{4})")
AS_ROLE = re.compile(r"(?i),\s*((?:Vice[-\s]?)?Chair(?:man|person|woman)?)\s*$")
AS_MIN_EMAILS = 18          # 21 of 21 today
AS_MIN_PHONES = 16          # 20 of 21 today; district 1 publishes "Confidential"
AS_MIN_WARD_PAIRS = 24      # 30 today, MEASURED off the page


def _as_lines(chunk):
    chunk = re.sub(r"(?i)<br\s*/?>", "\n", chunk)
    chunk = re.sub(r"<[^>]+>", " ", chunk)
    return [x for x in (re.sub(r"\s+", " ", l).strip()
                        for l in html_lib.unescape(chunk).replace("\xa0", " ").split("\n"))
            if x]


def scrape_ashland_board(spec):
    """All 21 seats or nothing, out of the county's own board page."""
    county, seats = spec["name"], spec["seats"]
    page = fetch(spec["source_url"])
    out, wards, munis, numbers, roles = {}, {}, {}, {}, {}
    for m in AS_BLOCK.finditer(page):
        district = int(m.group(1))
        if district in out:
            raise RuntimeError("%s: two blocks state district %d" % (county, district))
        head = AS_MAPLINK.sub(" ", m.group(2))
        head = AS_ALDER.sub("", _as_lines(head)[0] if _as_lines(head) else "")
        body = m.group(3)
        lines = _as_lines(body)
        if not lines:
            raise RuntimeError("%s: district %d's block carries no text after its "
                               "header — the page has reshaped" % (county, district))
        who = lines[0]
        role = None
        got = AS_ROLE.search(who)
        if got:
            role = re.sub(r"\s+", " ", got.group(1)).strip()
            who = AS_ROLE.sub("", who)
        if VACANT.search(who):
            out[district] = {"name": None, "vacant": True, "role": None}
        else:
            name = clean(who)[0]
            if not _reads_as_name(name):
                raise RuntimeError("%s: district %d resolved the name %r, which "
                                   "does not read as a name — re-read %s"
                                   % (county, district, name, spec["source_url"]))
            entry = {"name": name, "vacant": False, "role": None}
            mail = AS_MAIL.search(body)
            if mail:
                entry["email"] = mail.group(1).lower()
            tel = AS_PHONE.search(" ".join(lines))
            if tel:
                numbers[district] = ["-".join(tel.groups())]
            out[district] = entry
            if role:
                roles[district] = role
        if not head:
            raise RuntimeError("%s: district %d's header states no composition — "
                               "it is what witnesses the numbering"
                               % (county, district))
        wards[district], munis[district] = parse_composition(head)

    seen = sorted(out)
    if seen != list(range(1, seats + 1)):
        raise RuntimeError("%s: the page lists districts %s, not 1..%d — re-read %s"
                           % (county, seen, seats, spec["source_url"]))
    drop_shared_phones(county, numbers, out)
    live = [d for d, r in out.items() if not r["vacant"]]
    names = [out[d]["name"] for d in live]
    if len(set(names)) != len(names):
        raise RuntimeError("%s: the same person is filed under two districts (%s)"
                           % (county, sorted({n for n in names if names.count(n) > 1})))
    emails = sum(1 for d in live if out[d].get("email"))
    phones = sum(1 for d in live if out[d].get("phone"))
    own = sum(1 for d in live
              if (out[d].get("email") or "").endswith("@" + spec["domain"]))
    if emails < AS_MIN_EMAILS or phones < AS_MIN_PHONES:
        raise RuntimeError("%s: %d e-mails and %d phones across %d filled seats "
                           "(floors %d/%d) — the blocks have reshaped and contact "
                           "is being dropped silently"
                           % (county, emails, phones, len(live),
                              AS_MIN_EMAILS, AS_MIN_PHONES))
    if own != emails:
        raise RuntimeError("%s: %d of %d mailboxes are on %s — a block has shifted"
                           % (county, own, emails, spec["domain"]))
    print("  %-12s %d seats, %d phones, %d e-mails (district 1 publishes 'Phone: "
          "Confidential' and ships with none; no home address is read, and every "
          "block prints one)" % (county, seats, phones, emails), file=sys.stderr)
    ward_number_witness(spec["fips"], county, wards, seats,
                        min_pairs=AS_MIN_WARD_PAIRS, munis=munis)
    rows = {str(d): r for d, r in out.items()}
    return attach_unique_roles(roles, rows, county), spec["source_url"]


# --- Douglas: a four-column table keyed by ORDINAL WORDS ----------------------
#
# douglascountywi.gov/647/Members-by-District is a Telerik-authored table:
# District | Member | Address | Phone, one row per seat. THE DISTRICT IS AN
# ORDINAL WORD — "1st District", "2nd District", "21st District" — so a reader
# looking for "District n" finds NOTHING on this page and measures the county
# as publishing no district column. It publishes the best one in the state.
#
# THE MEMBER CELL IS THE MAILTO ANCHOR, and the address cell beside it is a
# HOME ADDRESS that is not read. A vacant seat carries the word in place of the
# anchor, with the county's own zero-width-space padding around it.
#
# A COMPOSITION IS PUBLISHED FOR EIGHT OF THE TWENTY-ONE AND IS DELIBERATELY
# NOT USED AS A WITNESS. The rural rows describe PARTS of municipalities in
# prose — "West 3/4 of the Town of Superior", "Summit (Southern portion)" —
# which parse_composition() reduces to municipalities that do not exist
# ("westofthe", "summitsouthernportion") because it is built for lists of whole
# municipalities and wards, not for fractions of them. A witness that scores
# junk against LTSB is worse than none: it either fails a correct county or,
# tuned until it passes, agrees with nothing in particular. So the district key
# here rests on the county's own ordinal column and the seat set being exactly
# 1..21 — Florence's position, for a different reason, and said rather than
# implied.
DOUGLAS_TABLE = {
    "fips": "55031", "name": "Douglas", "seats": 21,
    "source_url": "https://douglascountywi.gov/647/Members-by-District",
    "domain": "douglascountywi.gov",
}
DG_ROW = re.compile(r"(?is)<tr[^>]*>(.*?)</tr>")
DG_CELL = re.compile(r"(?is)<t[dh][^>]*>(.*?)</t[dh]>")
# THE ORDINAL IS NOT THE WHOLE CELL ON EVERY ROW. Superior's thirteen city
# districts print "1st District" and nothing else; the eight rural ones print
# their composition in the SAME cell — "16th District Towns of Brule,
# Cloverland, Lakeside and Maple". Anchored at the end, this matched thirteen
# rows of twenty-one and the seat-set gate refused the county.
DG_ORDINAL = re.compile(r"(?i)^\s*(\d{1,2})\s*(?:st|nd|rd|th)\s+District\b\s*(.*)$")
DG_MAIL = re.compile(r"(?i)mailto:\s*([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+)")
DG_PHONE = re.compile(r"\(?(\d{3})\)?[-.\s]?(\d{3})[-.\s](\d{4})")
DG_MIN_EMAILS = 16          # 20 of 20 filled seats today
DG_MIN_PHONES = 16          # 20 of 20


def _dg_text(chunk):
    chunk = re.sub(r"(?i)<br\s*/?>", " ", chunk)
    return re.sub(r"\s+", " ", html_lib.unescape(re.sub(r"<[^>]+>", " ", chunk))
                  .replace("\xa0", " ").replace("​", "")).strip()


def scrape_douglas_table(spec):
    """All 21 seats or nothing, out of the county's Members by District table."""
    county, seats = spec["name"], spec["seats"]
    page = fetch(spec["source_url"])
    out, numbers = {}, {}
    for row in DG_ROW.findall(page):
        cells = DG_CELL.findall(row)
        if len(cells) < 4:
            continue
        said = DG_ORDINAL.match(_dg_text(cells[0]))
        if not said:
            continue
        district = int(said.group(1))
        if district in out:
            raise RuntimeError("%s: two rows state district %d" % (county, district))
        who = _dg_text(cells[1])
        if VACANT.search(who) or not who:
            out[district] = {"name": None, "vacant": True, "role": None}
            continue
        name = clean(who)[0]
        if not _reads_as_name(name):
            raise RuntimeError("%s: district %d resolved the name %r, which does "
                               "not read as a name — re-read %s"
                               % (county, district, name, spec["source_url"]))
        entry = {"name": name, "vacant": False, "role": None}
        mail = DG_MAIL.search(cells[1])
        if mail:
            entry["email"] = mail.group(1).lower()
        # CELL 2 IS THE HOME ADDRESS AND IS NOT READ.
        tel = DG_PHONE.search(_dg_text(cells[3]))
        if tel:
            numbers[district] = ["-".join(tel.groups())]
        out[district] = entry

    seen = sorted(out)
    if seen != list(range(1, seats + 1)):
        raise RuntimeError("%s: the table lists districts %s, not 1..%d — re-read %s"
                           % (county, seen, seats, spec["source_url"]))
    drop_shared_phones(county, numbers, out)
    live = [d for d, r in out.items() if not r["vacant"]]
    names = [out[d]["name"] for d in live]
    if len(set(names)) != len(names):
        raise RuntimeError("%s: the same person is filed under two districts (%s)"
                           % (county, sorted({n for n in names if names.count(n) > 1})))
    emails = sum(1 for d in live if out[d].get("email"))
    phones = sum(1 for d in live if out[d].get("phone"))
    if emails < DG_MIN_EMAILS or phones < DG_MIN_PHONES:
        raise RuntimeError("%s: %d e-mails and %d phones across %d filled seats "
                           "(floors %d/%d) — the table has reshaped and contact is "
                           "being dropped silently"
                           % (county, emails, phones, len(live),
                              DG_MIN_EMAILS, DG_MIN_PHONES))
    vacant = sorted(d for d, r in out.items() if r["vacant"])
    print("  %-12s %d seats, %d filled, %d phones, %d e-mails (the address column "
          "is home addresses and is never read)"
          % (county, seats, len(live), phones, emails), file=sys.stderr)
    if vacant:
        print("  note %-12s the county marks district %s vacant in its own table"
              % (county, ", ".join(str(d) for d in vacant)), file=sys.stderr)
    print("  witness %-12s districts read from the county's ORDINAL column "
          "(1st..%dst); the eight rural rows also describe their composition, in "
          "prose about PARTS of municipalities, which is not reduced to a ward "
          "set — so the key rests on that column and the seat set"
          % (county, seats), file=sys.stderr)
    return {str(d): r for d, r in out.items()}, spec["source_url"]


# --- Sawyer: CivicPlus's NEW responsive directory, which is not the h-card one -
#
# THE FLEET'S FIRST COUNTY ON CIVICPLUS'S REWRITTEN STAFF DIRECTORY. Door and
# Oconto are CivicPlus too and share HCARD_* above — <li class="widgetItem
# h-card"> with p-name, p-job-title, p-tel fields. Sawyer's directory has none
# of that: it is Bootstrap list-group rows, zero h-cards, zero p-name. A reader
# that assumed "CivicPlus means h-cards" measures this county as publishing
# nothing. THE PLATFORM IS NOT THE MARKUP, and other counties will migrate.
#
# THE CANONICAL URL REDIRECTS INTO THE NEW ONE. /directory.aspx?did=33 answers
# 302 to /m/directory/department?did=33 — the `/m/` path is not a mobile
# variant to be avoided, it is where this template lives now. The .aspx form is
# fetched because it is the stable CivicPlus address and follows the template
# wherever it goes next.
#
# THE JOB TITLE IS PRINTED TWICE PER ROW AND BOTH COPIES MUST AGREE. The
# template emits one for each breakpoint (`d-sm-block d-none` and `d-sm-none
# d-block`), so every row states its district twice. Unlike Forest — where the
# duplicate headings belong to NEIGHBOURING members and only the first may be
# read — these are the same member's, so the honest use is to require them
# equal rather than to pick one.
#
# THE COMPOSITION IS ON A THIRD PAGE. The directory names people and the board
# page is prose; /264/Supervisory-Districts publishes all fifteen districts'
# towns, villages, cities and wards, which is what makes the ward witness
# possible here where Florence had none.
#
# THAT PAGE ALSO FOUND A SILENT DEFECT IN THE SHARED COMPOSITION PARSER.
# Sawyer writes "City of Hayward Wards 5 and 6", and COMP_WARDS continued a
# ward run across , & – and - but NOT across the word "and" — so ward 6 fell
# out of the run and was dropped without a word, while the witness printed a
# confident ratio over the smaller number. Fixed at COMP_WARDS; see the note
# there.
#
# EACH MEMBER'S OWN EMPLOYEE PAGE IS THE SECOND SURFACE, restating the name and
# "District N Supervisor" independently of the row it was read from.
#
# TWO COUNTY MAIL DOMAINS ARE IN USE — sawyercountygov.org and sawyercounty.gov
# — and both are the county's; each address ships exactly as published.
#
# NO CHAIR IS NAMED ON ANY COUNTY SURFACE, so no role ships. The Blue Book has
# one and build_wi_county_officer_roster.py already reconciles that separately;
# inventing a title here from a book the county has not confirmed is not this
# scraper's job.
SAWYER_DIRECTORY = {
    "fips": "55113", "name": "Sawyer", "seats": 15,
    "source_url": "https://www.sawyercounty.gov/directory.aspx?did=33",
    "composition_url": "https://www.sawyercounty.gov/264/Supervisory-Districts",
}
SW_ROW = re.compile(r'(?is)<li class="list-group-item[^"]*"[^>]*>(.*?)</li>')
SW_LINK = re.compile(r'(?is)<a href="([^"]*employee\?eid=\d+)"[^>]*>(.*?)</a>')
SW_TITLE = re.compile(r'(?is)<div class="[^"]*\bd-(?:sm-block d-none|sm-none d-block)\b[^"]*"[^>]*>(.*?)</div>')
SW_DISTRICT = re.compile(r"(?i)^District\s*(\d+)\s*Supervisor$")
SW_MAIL = re.compile(r'(?i)mailto:([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+)')
SW_PHONE = re.compile(r"\(?(\d{3})\)?[-.\s]?(\d{3})[-.\s](\d{4})")
SW_COMP = re.compile(r"(?i)District\s*(\d+)\s*[-–]\s*([^\n<]{4,300})")
SW_MIN_EMAILS = 13          # 15 of 15 today
SW_MIN_PHONES = 9           # 11 of 15 today; four publish none
SW_MIN_WARD_PAIRS = 20      # 27 today, MEASURED off the composition page


def _sw_text(chunk):
    return re.sub(r"\s+", " ", html_lib.unescape(
        re.sub(r"<[^>]+>", " ", chunk)).replace("\xa0", " ")).strip()


def scrape_sawyer_directory(spec):
    """All 15 seats or nothing, witnessed by each member's own employee page."""
    county, seats = spec["name"], spec["seats"]
    page = fetch(spec["source_url"])
    rows = SW_ROW.findall(page)
    if not rows:
        raise RuntimeError("%s: no directory rows on %s — the county has moved off "
                           "this template; re-read the page"
                           % (county, spec["source_url"]))

    out, links, numbers = {}, {}, {}
    for row in rows:
        link = SW_LINK.search(row)
        if not link:
            continue
        titles = [t for t in (_sw_text(x) for x in SW_TITLE.findall(row)) if t]
        if not titles:
            raise RuntimeError("%s: a directory row states no job title (%r) — the "
                               "district is read from it, so this cannot ship"
                               % (county, _sw_text(link.group(2))[:40]))
        # BOTH BREAKPOINT COPIES ARE THIS MEMBER'S AND MUST AGREE — see above.
        if len(set(titles)) != 1:
            raise RuntimeError("%s: a row prints its title as %s — the template's "
                               "two copies disagree, which is what a reshaped row "
                               "looks like" % (county, sorted(set(titles))))
        said = SW_DISTRICT.match(titles[0])
        if not said:
            raise RuntimeError("%s: a directory row is titled %r rather than "
                               "'District N Supervisor' — re-read %s"
                               % (county, titles[0], spec["source_url"]))
        district = int(said.group(1))
        if district in out:
            raise RuntimeError("%s: two rows state district %d" % (county, district))
        who = _sw_text(link.group(2))
        if VACANT.search(who):
            out[district] = {"name": None, "vacant": True, "role": None}
            links[district] = urllib.parse.urljoin(spec["source_url"], link.group(1))
            continue
        name = clean(who)[0]
        if not _reads_as_name(name):
            raise RuntimeError("%s: district %d resolved the name %r, which does "
                               "not read as a name — re-read %s"
                               % (county, district, name, spec["source_url"]))
        entry = {"name": name, "vacant": False, "role": None}
        mail = SW_MAIL.search(row)
        if mail:
            entry["email"] = mail.group(1).lower()
        tel = SW_PHONE.search(_sw_text(row))
        if tel:
            numbers[district] = ["-".join(tel.groups())]
        out[district] = entry
        links[district] = urllib.parse.urljoin(spec["source_url"], link.group(1))

    seen = sorted(out)
    if seen != list(range(1, seats + 1)):
        raise RuntimeError("%s: the directory lists districts %s, not 1..%d — "
                           "re-read %s" % (county, seen, seats, spec["source_url"]))

    drop_shared_phones(county, numbers, out)

    live = [d for d, r in out.items() if not r["vacant"]]
    names = [out[d]["name"] for d in live]
    if len(set(names)) != len(names):
        raise RuntimeError("%s: the same person is filed under two districts (%s)"
                           % (county, sorted({n for n in names if names.count(n) > 1})))

    # EACH MEMBER'S OWN EMPLOYEE PAGE: the name and the district, again.
    for n, district in enumerate(sorted(out)):
        if n:
            time.sleep(0.4)             # 15 pages of somebody else's server
        own = _sw_text(fetch(links[district]))
        want = "District %d Supervisor" % district
        if want.lower() not in own.lower():
            raise RuntimeError("%s: district %d's own employee page does not state "
                               "%r — the directory row and the member's own page "
                               "disagree about which seat this is (%s)"
                               % (county, district, want, links[district]))
        if not out[district]["vacant"] and \
                name_fold(out[district]["name"]) not in name_fold(own):
            raise RuntimeError("%s: the directory files district %d to %r and that "
                               "member's own page does not name them — the two "
                               "county surfaces disagree about who this is"
                               % (county, district, out[district]["name"]))

    emails = sum(1 for d in live if out[d].get("email"))
    phones = sum(1 for d in live if out[d].get("phone"))
    if emails < SW_MIN_EMAILS or phones < SW_MIN_PHONES:
        raise RuntimeError("%s: %d e-mails and %d phones across %d filled seats "
                           "(floors %d/%d) — the rows have reshaped and contact is "
                           "being dropped silently"
                           % (county, emails, phones, len(live),
                              SW_MIN_EMAILS, SW_MIN_PHONES))

    print("  %-12s %d seats, %d phones, %d e-mails across two county mail domains, "
          "both shipped as published" % (county, seats, phones, emails),
          file=sys.stderr)
    print("  witness %-12s %d/%d seats' own employee pages confirm their name and "
          "district" % (county, seats, seats), file=sys.stderr)

    # THE THIRD PAGE: the county's own district-to-ward composition.
    wards, munis = {}, {}
    try:
        comp = fetch(spec["composition_url"])
    except Exception as e:      # noqa: BLE001 - the witness, never the source
        print("  WITNESS SKIPPED %-9s the Supervisory Districts page is "
              "unreachable (%s) — the roster ships unwitnessed this run"
              % (county, e), file=sys.stderr)
        comp = None
    if comp:
        flat = re.sub(r"(?i)<br\s*/?>|</(p|div|li)>", "\n", comp)
        flat = html_lib.unescape(re.sub(r"<[^>]+>", " ", flat))
        for m in SW_COMP.finditer(flat):
            d = int(m.group(1))
            if d in out:
                wards[d], munis[d] = parse_composition(m.group(2))
        if sorted(wards) != list(range(1, seats + 1)):
            raise RuntimeError("%s: the Supervisory Districts page states %s, not "
                               "districts 1..%d — re-read %s"
                               % (county, sorted(wards), seats,
                                  spec["composition_url"]))
        ward_number_witness(spec["fips"], county, wards, seats,
                            min_pairs=SW_MIN_WARD_PAIRS, munis=munis)
    rows_out = {str(d): r for d, r in out.items()}
    return rows_out, spec["source_url"]


# --- Florence: the same vendor CMS again, with a seat the county leaves empty -
#
# THE THIRD COUNTY ON THIS CMS (after Menominee and Langlade), which is why the
# readers it shares are named DMI_* rather than LG_* now. Its board list carries
# the same <b>Chairperson</b> / <b>Vice-Chair</b> / <b>Board Members</b>
# headings over "Surname, Given - District # N" rows, and the same ?i=<hash>
# page per member restating Name, District #, Phone Number and Email Address.
#
# THE PAGE THE RECORD HAD ON FILE WAS THE COUNTY HOME PAGE. Its board list is
# at /government/boards_and_committees/ — the fifth county running whose roster
# was one link from a URL this repo already carried.
#
# ONE ROW IS A SEAT, NOT A PERSON, AND is_name() WOULD HAVE SHIPPED IT. The
# county files its empty seat as a member: the list reads "Position, Vacant"
# and the member page behind it says Name: Vacant Position, District #: 1. Read
# the way Langlade's rows are read, that flips to "Vacant Position", passes
# is_name() — two capitalised words — and ships as District 1's supervisor. The
# vacancy is therefore tested BEFORE the name is built, on both surfaces, and
# the seat renders as the vacancy it is.
#
# THERE IS NO WARD OR MUNICIPALITY WITNESS HERE AND THAT IS A MEASUREMENT.
# Langlade's rows carry the towns and wards after the district number; Florence
# writes "- District # 2" and stops, on every row, and no other county surface
# states a composition either. So the district key rests on the two statements
# the county does make — the list's row and that member's own page, which must
# agree — plus the seat set being exactly 1..12. That is weaker than Barron's
# 63/63 wards and it is what this county publishes; inventing a composition
# from LTSB's own file to check LTSB with is not a witness.
#
# A THIRD COUNTY SURFACE NAMES THE ELEVEN. /government/committees/?committees=
# <hash> for the County Board lists the members with no districts, and the
# eleven filled seats must be exactly that set — a check the vacancy would
# otherwise hide, since a list of eleven under a twelve-seat board looks like a
# missed row from either direction.
#
# SIX OF THE ELEVEN MAILBOXES ARE PERSONAL ADDRESSES — gmail, outlook, yahoo,
# chartermi.net, florwi.org — and five are on florencecountywi.gov. THE COUNTY
# PUBLISHES EACH ONE AS THE WAY TO REACH THAT SUPERVISOR, so each ships as
# published; a county-domain gate of the kind St. Croix's table gets would
# refuse this county for how its supervisors take mail. For the same reason
# there is no surname-agreement check on the address here: cskel@chartermi.net
# is Charles Kellstrom and maddmatt45@yahoo.com is Matt Brunette, and a gate
# demanding the surname would fail on real, correct rows. NOTE THE COUNTY'S OWN
# DOMAINS DIFFER: the site is florencecountywi.com and the mailboxes are
# florencecountywi.gov.
#
# EVERY MEMBER PAGE PRINTS A HOME ADDRESS AND NONE IS READ.
FLORENCE_BOARD = {
    "fips": "55037", "name": "Florence", "seats": 12,
    "source_url": "https://www.florencecountywi.com/government/boards_and_committees/",
    "board_url": ("https://www.florencecountywi.com/government/committees/"
                  "?committees=8a8ed99cd68d"),
}
FL_VACANT_ROW = re.compile(r"(?i)^\s*position\s*,\s*vacant\s*$")
FL_VACANT_OWN = re.compile(r"(?i)^\s*vacant\s+position\s*$")
FL_MEMBER_BLOCK = re.compile(r"(?is)County Board Members\s*:?(.*?)(?:<h\d|Minutes)")
FL_MIN_PHONES = 9           # 11 of 11 filled seats today
FL_MIN_EMAILS = 9           # 11 of 11


def scrape_florence_board(spec):
    """All 12 seats or nothing, each witnessed by that member's own page."""
    county, seats = spec["name"], spec["seats"]
    page = fetch(spec["source_url"])
    heads = [(m.start(), m.group(1)) for m in DMI_HEAD.finditer(page)]
    if len(heads) != 3:
        raise RuntimeError("%s: the page carries %d of its three office headings "
                           "(Chairperson, Vice-Chair, Board Members) — it has "
                           "been rebuilt; re-read %s"
                           % (county, len(heads), spec["source_url"]))

    out, roles, links = {}, {}, {}
    for n, (start, office) in enumerate(heads):
        end = heads[n + 1][0] if n + 1 < len(heads) else len(page)
        for m in DMI_ROW.finditer(page[start:end]):
            district = int(m.group("district"))
            if district in out:
                raise RuntimeError("%s: two rows state district %d" % (county, district))
            listed = html_lib.unescape(m.group("name"))
            links[district] = urllib.parse.urljoin(
                spec["source_url"], html_lib.unescape(m.group("url")))
            # THE VACANCY IS TESTED BEFORE THE NAME IS BUILT — see the note
            # above; "Position, Vacant" flips to a plausible person otherwise.
            if FL_VACANT_ROW.match(listed):
                out[district] = {"name": None, "vacant": True, "role": None}
                if office != "Board Members":
                    raise RuntimeError("%s: district %d is vacant and sits under "
                                       "the %r heading — an empty seat cannot "
                                       "hold an office" % (county, district, office))
                continue
            name = surname_first(county, listed)
            # _reads_as_name(), NOT is_name(): district 8 is "John (Jack)
            # Bomberg" and the per-token test rejects "(Jack)". This file
            # already answered that for Richland's "Melvin (Bob) Frank" — the
            # nickname is stripped for the TEST and the county's own spelling
            # is what ships — so this reuses it rather than loosening is_name,
            # which a first draft here did and which silently shadowed the
            # existing NICKNAME pattern.
            if not _reads_as_name(name):
                raise RuntimeError("%s: district %d resolved the name %r, which "
                                   "does not read as a name — re-read %s"
                                   % (county, district, name, spec["source_url"]))
            out[district] = {"name": name, "vacant": False, "role": None}
            if office != "Board Members":
                roles[district] = office

    seen = sorted(out)
    if seen != list(range(1, seats + 1)):
        raise RuntimeError("%s: the page lists districts %s, not 1..%d — the "
                           "board's composition has changed; re-read %s"
                           % (county, seen, seats, spec["source_url"]))
    named = [r["name"] for r in out.values() if not r["vacant"]]
    if len(set(named)) != len(named):
        raise RuntimeError("%s: the same person is filed under two districts (%s)"
                           % (county, sorted({n for n in named if named.count(n) > 1})))

    phones = emails = 0
    for n, district in enumerate(sorted(out)):
        if n:
            time.sleep(0.4)             # 12 pages of somebody else's server
        own = dmi_flat(fetch(links[district]))
        said_name, said_dist = DMI_OWN_NAME.search(own), DMI_OWN_DIST.search(own)
        if not (said_name and said_dist):
            raise RuntimeError("%s: district %d's own page states no Name/District "
                               "pair — the member pages have reshaped and the "
                               "list's district would be unwitnessed (%s)"
                               % (county, district, links[district]))
        if int(said_dist.group(1)) != district:
            raise RuntimeError("%s: the list files district %d and that member's "
                               "own page says %s — the two county surfaces "
                               "disagree about which seat this is"
                               % (county, district, said_dist.group(1)))
        if out[district]["vacant"]:
            # THE SECOND SURFACE MUST ALSO SAY EMPTY. A list that still reads
            # "Position, Vacant" over a page that now names somebody is a seat
            # that has been filled and half-updated, and shipping the vacancy
            # would tell that district it has no supervisor when it does.
            if not FL_VACANT_OWN.match(said_name.group(1)):
                raise RuntimeError("%s: the list files district %d as vacant and "
                                   "its own page names %r — the seat may have "
                                   "been filled; re-read both"
                                   % (county, district, said_name.group(1).strip()))
            continue
        if name_fold(said_name.group(1)) != name_fold(out[district]["name"]):
            raise RuntimeError("%s: the list files %r where their own page says "
                               "%r — the two county surfaces disagree about who "
                               "this is" % (county, out[district]["name"],
                                            said_name.group(1).strip()))
        tel = DMI_PHONE.search(own)
        if tel:
            out[district]["phone"] = "-".join(tel.groups())
            phones += 1
        mail = DMI_MAIL.search(own)
        if mail:
            # AS PUBLISHED — see the note above on the six personal addresses.
            out[district]["email"] = mail.group(1).lower()
            emails += 1

    live = [d for d, r in out.items() if not r["vacant"]]
    if phones < FL_MIN_PHONES or emails < FL_MIN_EMAILS:
        raise RuntimeError("%s: %d phones and %d e-mails across %d filled seats "
                           "(floors %d/%d) — the member pages have reshaped and "
                           "contact is being dropped silently"
                           % (county, phones, emails, len(live),
                              FL_MIN_PHONES, FL_MIN_EMAILS))

    # THE THIRD SURFACE: the County Board committee page's own member list.
    try:
        board = FL_MEMBER_BLOCK.search(fetch(spec["board_url"]))
    except Exception as e:      # noqa: BLE001 - the witness, never the source
        print("  WITNESS SKIPPED %-9s the County Board committee page is "
              "unreachable (%s) — the roster ships without its third surface "
              "this run" % (county, e), file=sys.stderr)
        board = None
    if board:
        # THE NAMES ARE ANCHOR TEXTS INSIDE TABLE CELLS, not lines: a first
        # draft split the block on <br> and paragraph tags and compared eleven
        # flattened <td bgcolor=...> strings against eleven names. The witness
        # caught it, which is the point of having it.
        listed = {name_fold(clean(html_lib.unescape(t))[0])
                  for t in re.findall(r"(?is)<a[^>]*>([^<]{2,60})</a>", board.group(1))
                  if _reads_as_name(clean(html_lib.unescape(t))[0])}
        ours = {name_fold(out[d]["name"]) for d in live}
        if listed != ours:
            raise RuntimeError(
                "%s: the County Board page names %s and the district list names "
                "%s — two county surfaces disagree about who sits on this board"
                % (county, sorted(listed - ours) or "no one extra",
                   sorted(ours - listed) or "no one extra"))
        print("  witness %-12s %d/%d filled seats appear on the county's separate "
              "County Board page" % (county, len(ours), len(live)), file=sys.stderr)

    vacant = sorted(d for d, r in out.items() if r["vacant"])
    print("  %-12s %d seats, %d filled, %d phones, %d e-mails (%d of them on the "
          "county's own domain and the rest personal addresses it publishes as "
          "the way to reach that supervisor; no home address is read)"
          % (county, seats, len(live), phones, emails,
             sum(1 for d in live if (out[d].get("email") or "")
                 .endswith("@florencecountywi.gov"))), file=sys.stderr)
    if vacant:
        print("  note %-12s the county files district %s as an empty seat on BOTH "
              "its surfaces — the list row reads 'Position, Vacant' and would "
              "otherwise flip to a plausible person's name"
              % (county, ", ".join(str(d) for d in vacant)), file=sys.stderr)
    print("  witness %-12s %d/%d seats' own pages confirm their district; no ward "
          "or municipality composition is published for this county, so the key "
          "rests on those two statements and the seat set"
          % (county, seats, seats), file=sys.stderr)
    rows = {str(d): r for d, r in out.items()}
    return attach_unique_roles(roles, rows, county), spec["source_url"]


# --- Barron: the county's OTHER site, one click from the page we already had ---
#
# THE COUNTY RUNS TWO SITES AND THE ROSTER IS ON THE ONE NOBODY LOOKED AT.
# barroncountywi.gov is the modern CMS; its County Board page is 75 KB of prose
# and names TWO people. www.co.barron.wi.us is the county's older ColdFusion
# site, where the committee lists, department heads, municipal officers, fire
# wardens and meeting archives all still live — and /board.cfm is a complete
# district-keyed table: all 29 districts, each with the municipalities and wards
# it is made of, its supervisor, a phone, and a county mailbox.
#
# THIS FILE HAD BOTH HALVES OF THE ANSWER AND NEVER JOINED THEM. The gap record
# put Barron among the counties that "answer 503", and the 2026-08-26 sweep that
# corrected it got as far as the right conclusion — "neither is the county:
# barroncountywi.gov and co.shawano.wi.us both serve their board pages" — put
# barroncountywi.gov in build_wi_county_board_directory.py's table, and stopped
# there. IT NEVER ASKED WHETHER THAT PAGE NAMES ANYONE. It does not; but it
# LINKS this one, twice, under the anchor text "Individual Contact Information
# for County Board Supervisors" and "Individual County Board Supervisor Contact
# Information". That is the St. Croix shape a third time: the page this repo had
# on file is prose and the table is one click further, behind a link that says
# exactly what it is. A CORRECTION THAT FIXES A LINK IS NOT A LOOK AT A COUNTY.
#
# THE BARE HOST IS NOT THE WWW HOST, and that is why the 503/reset record read
# as final. co.barron.wi.us resolves to 173.248.55.40 and fails the TLS
# handshake from here; www.co.barron.wi.us resolves to 173.248.55.39 and answers
# 200 with the table, reproducibly, over both HTTP/1.1 and h2. WHAT THIS PROJECT
# CANNOT SAY IS WHY THE BARE ONE FAILS: this sandbox's egress gateway re-signs
# every certificate, so the chain openssl prints for that host is the proxy's
# and not the county's, and a reset seen here may be the proxy's too. The
# scraper's vantage is CI, the record says only what was measured, and the host
# that ships is the one that answered. (Marathon and Racine taught the same
# lesson from the other side — a 301 to www that a redirect-following probe
# recorded as the final 403.)
#
# THE DISTRICT NUMBER IS IN THE ROW ABOVE THE SUPERVISOR'S ROW. Each seat is
# TWO <tr>s: a 3-cell row carrying the number, the composition and a link to
# that district's map PDF, then a 5-cell row whose first cell is empty and whose
# other four are name, address, phone and mailbox. A reader that flattens the
# table and walks cells pairs every supervisor with nothing at all, and one that
# takes "the first number in the row" pairs them with a house number. So the
# rows are paired explicitly, and a 3-cell row that is not followed by its
# 5-cell partner fails the county rather than shifting the rest by one — the
# Franklin grid trap in a different vendor's markup.
#
# THE ADDRESS COLUMN IS NEVER READ. It is 28 home addresses (District 2's cell
# is the literal string ",", which is what a supervisor who publishes none looks
# like here). No county in this fleet ships one.
#
# THE OFFICER BLOCK STATES ITS THREE ROLES TWICE, IN TWO FORMATS, and both are
# required to agree: a list ("Louie Okey, Chairman") and the photo caption below
# it ("L-R: Louie Okey-Chair, ..."). Two renderings of one fact on one page is a
# weaker witness than two pages, and it is what this county publishes; it would
# still catch the caption and the list drifting apart, which is how a board that
# has re-organised usually looks before someone updates both.
BARRON_TABLE = {
    "fips": "55005", "name": "Barron", "seats": 29,
    "source_url": "https://www.co.barron.wi.us/board.cfm",
    "domain": "co.barron.wi.us",
}
BR_ROW = re.compile(r"(?is)<tr[^>]*>(.*?)</tr>")
BR_CELL = re.compile(r"(?is)<t[dh][^>]*>(.*?)</t[dh]>")
BR_MAIL = re.compile(r"(?i)\b([A-Za-z0-9._%+-]+@co\.barron\.wi\.us)\b")
BR_PHONE = re.compile(r"(?<!\d)(\d{3})[-.\s](\d{3})[-.\s](\d{4})(?!\d)")
# "Louie Okey, Chairman" — the list. The caption is "Louie Okey-Chair".
BR_LIST_ROLE = re.compile(r"(?i)([A-Z][A-Za-z.'\-]+(?:\s+[A-Z][A-Za-z.'\-]+){1,3})\s*,\s*"
                          r"((?:2nd\s+)?(?:Vice\s+)?Chair(?:man|person|woman)?)\b")
BR_CAPTION_ROLE = re.compile(r"(?i)([A-Z][A-Za-z.'\-]+(?:\s+[A-Z][A-Za-z.'\-]+){1,3})\s*-\s*"
                             r"((?:2nd\s+)?(?:Vice\s+)?Chair(?:man|person|woman)?)\b")
BR_MIN_EMAILS = 26          # 28 of 29 today; District 7 publishes none
BR_MIN_PHONES = 27          # 29 of 29 today
BR_MIN_WARD_PAIRS = 55      # 63 today, and 63 is the whole of what this page
                            # can give: nine of the 29 districts name a
                            # municipality with NO ward (District 4 is
                            # "Town of Prairie Lake" entire), which
                            # contributes to the municipality-set check and
                            # to no ward pair. The first floor here was 90,
                            # guessed from St. Croix's 131 rather than
                            # measured, and it failed the county on its own
                            # invention — a floor is a measurement of what
                            # the source publishes, never a target for it.


def _br_flat(cell):
    """One table cell as text."""
    cell = re.sub(r"(?i)<br\s*/?>", " ", cell)
    cell = re.sub(r"<[^>]+>", " ", cell)
    return re.sub(r"\s+", " ", html_lib.unescape(cell).replace("\xa0", " ")).strip()


def _br_role(text):
    """{name: role} from one rendering of the officer block."""
    out = {}
    for pattern in (BR_LIST_ROLE, BR_CAPTION_ROLE):
        got = {}
        for who, what in pattern.findall(text):
            got[clean(who)[0]] = re.sub(r"\s+", " ", what).strip()
        if got:
            out.setdefault(id(pattern), got)
    return out


def scrape_barron_table(spec):
    """All 29 seats or nothing, out of the county's own board.cfm table."""
    county, seats = spec["name"], spec["seats"]
    page = fetch(spec["source_url"])

    rows = BR_ROW.findall(page)
    if not rows:
        raise RuntimeError("%s: no table rows on %s — the page has been rebuilt; "
                           "re-read it" % (county, spec["source_url"]))

    out, wards, munis, numbers, pending = {}, {}, {}, {}, None
    for row in rows:
        cells = [_br_flat(c) for c in BR_CELL.findall(row)]
        raw = BR_CELL.findall(row)
        if len(cells) == 3 and re.fullmatch(r"\d{1,2}", cells[0]):
            if pending is not None:
                raise RuntimeError(
                    "%s: district %s's row is followed by another district row "
                    "rather than by its supervisor — the two-row pairing has "
                    "broken and every seat below would shift" % (county, pending[0]))
            pending = (cells[0], cells[1])
            continue
        if len(cells) == 5 and cells[0] == "" and pending is not None:
            district = int(pending[0])
            name = clean(cells[1])[0]
            if not is_name(name):
                raise RuntimeError("%s: district %d resolved the name %r — that is "
                                   "not a name, and the columns have shifted"
                                   % (county, district, name))
            entry = {"name": name, "vacant": False, "role": None}
            # CELL 2 IS THE HOME ADDRESS AND IS NOT READ.
            got = BR_PHONE.search(cells[3])
            if got:
                numbers[district] = ["-".join(got.groups())]
            mail = BR_MAIL.search(raw[4])
            if mail:
                entry["email"] = mail.group(1).lower()
            wards[district], munis[district] = parse_composition(pending[1])
            if not munis[district]:
                raise RuntimeError("%s: district %d's composition names no "
                                   "municipality (%r) — that column is what "
                                   "witnesses the numbering, so this cannot ship "
                                   "unchecked" % (county, district, pending[1][:80]))
            out[district] = entry
            pending = None
    if pending is not None:
        raise RuntimeError("%s: district %s's row has no supervisor row after it — "
                           "the table ends mid-seat" % (county, pending[0]))

    seen = sorted(out)
    if seen != list(range(1, seats + 1)):
        raise RuntimeError("%s: the table lists districts %s, not 1..%d — re-read "
                           "%s" % (county, seen, seats, spec["source_url"]))

    drop_shared_phones(county, numbers, out)

    names = [r["name"] for r in out.values()]
    if len(set(names)) != len(names):
        dupes = sorted({n for n in names if names.count(n) > 1})
        raise RuntimeError("%s: the same person is filed under two districts (%s)"
                           % (county, dupes))

    emails = sum(1 for r in out.values() if r.get("email"))
    phones = sum(1 for r in out.values() if r.get("phone"))
    agree = sum(1 for r in out.values() if r.get("email")
                and name_fold(r["name"].split()[-1]) in name_fold(r["email"].split("@")[0]))
    if emails < BR_MIN_EMAILS or phones < BR_MIN_PHONES:
        raise RuntimeError("%s: %d e-mails and %d phones across %d seats (floors "
                           "%d/%d) — the contact columns have reshaped and contact "
                           "is being dropped silently"
                           % (county, emails, phones, seats,
                              BR_MIN_EMAILS, BR_MIN_PHONES))
    if agree < emails - 1:
        raise RuntimeError("%s: only %d of %d mailboxes carry their own "
                           "supervisor's surname — a row has shifted"
                           % (county, agree, emails))

    # THE OFFICER BLOCK, STATED TWICE ON THE PAGE IN TWO FORMATS.
    head = page[:page.index("board.cfm") if "board.cfm" in page else len(page)]
    block = _br_flat(page[:page.index("Related Documents")]) \
        if "Related Documents" in page else _br_flat(page)
    listed = {clean(w)[0]: re.sub(r"\s+", " ", r).strip()
              for w, r in BR_LIST_ROLE.findall(block)}
    caption = {clean(w)[0]: re.sub(r"\s+", " ", r).strip()
               for w, r in BR_CAPTION_ROLE.findall(block)}
    if not listed or not caption:
        raise RuntimeError("%s: the officer block no longer states its roles both "
                           "ways (list %s, caption %s) — it is the only check on "
                           "who chairs this board" % (county, listed, caption))
    if set(listed) != set(caption):
        raise RuntimeError("%s: the officer list names %s and the photo caption "
                           "names %s — the page's two statements disagree and "
                           "neither is guessed at"
                           % (county, sorted(listed), sorted(caption)))
    for who, what in list(listed.items()):
        low = what.lower()
        norm = ("2nd Vice Chair" if low.startswith("2nd")
                else "Vice Chair" if "vice" in low else "Chair")
        cap = caption[who].lower()
        cap_norm = ("2nd Vice Chair" if cap.startswith("2nd")
                    else "Vice Chair" if "vice" in cap else "Chair")
        if norm != cap_norm:
            raise RuntimeError("%s: %s is %r in the list and %r in the caption"
                               % (county, who, what, caption[who]))
        listed[who] = norm
    del head

    # THE OFFICER BLOCK NAMES PEOPLE; attach_unique_roles() KEYS ON DISTRICTS.
    # The first draft here passed the name-keyed dict straight in, and it did
    # exactly nothing: every lookup was districts.get("Louie Okey"), every miss
    # was silent, and the run printed three officers it had not attached while
    # all 29 seats, both witnesses and every count guard stayed green. So the
    # join is explicit and it FAILS rather than shrugging — an officer the
    # table does not name, or names twice, is a page that has moved out from
    # under this reader, not a title to drop quietly. The join is printed each
    # run, the way Vermilion's surname flip and Clay's role join are.
    by_district = {}
    for who, role in sorted(listed.items()):
        hits = [d for d, r in out.items() if name_fold(r["name"]) == name_fold(who)]
        if len(hits) != 1:
            raise RuntimeError("%s: the officer block names %r as %s and the "
                               "table matches %d supervisors — a role is never "
                               "attached to a guess"
                               % (county, who, role, len(hits)))
        by_district[hits[0]] = role
        print("  join %-12s %s (%s) -> district %d"
              % (county, who, role, hits[0]), file=sys.stderr)

    print("  %-12s %d seats, %d phones, %d e-mails (the address column is 28 "
          "home addresses and is never read)"
          % (county, seats, phones, emails), file=sys.stderr)
    print("  witness %-12s %d/%d mailboxes carry their own supervisor's surname; "
          "officers %s stated twice on the page and agreeing"
          % (county, agree, emails,
             ", ".join("%s (%s)" % (k, v) for k, v in sorted(listed.items()))),
          file=sys.stderr)
    ward_number_witness(spec["fips"], county, wards, seats,
                        min_pairs=BR_MIN_WARD_PAIRS, munis=munis)
    rows_out = {str(d): r for d, r in out.items()}
    return attach_unique_roles(by_district, rows_out, county), spec["source_url"]


# --- Forest: GoDaddy ContentCards, where two of every three names are wrong ---
#
# co.forest.wi.gov/county-board-supervisors answers 200 and names all 21
# districts. The county HOME page — the URL this repo had on file — names
# nobody, which is the Barron and St. Croix shape a fourth time, and the reason
# the record read "Forest does not resolve" was never re-tested against the
# page a reader actually lands on. NOTE THE DIRECTION IS THE OPPOSITE OF
# BARRON'S: here the bare host answers and `www.` fails, so neither prefix is
# the safe default and the working one is a measurement per county.
#
# THE PAGE GIVES EVERY SUPERVISOR THREE <h4> HEADINGS AND TWO OF THEM ARE
# SOMEBODY ELSE. This is a GoDaddy Website Builder site: each seat is a
# ContentCard whose Block holds three ContentCardHeading elements, one shown per
# breakpoint, and the two hidden ones carry the names of NEIGHBOURING cards.
# District 4's card reads "Scott Goode", "Brian Piasini", "Sam Augustin- County
# Board Chair" in that order; only the first is District 4's supervisor. A
# reader that takes the last <h4>, or joins them, or searches the card for a
# name, ships two thirds of this board wrong — and it would look entirely
# plausible, because every name on the page is a real Forest County supervisor.
# ONLY h4[0] IS THE SEAT'S OWN. `data-aid="CONTENT_HEADLINE1_RENDERED"` marks
# the right one on FOUR of the twenty-one cards and nothing on the rest, so
# that attribute cannot be the selector either; position is.
#
# THE SAME LEAK MAKES THE VACANCY TEST PER-HEADING, NOT PER-CARD. Four seats
# are empty and the county says so in the name itself — "District 12 - Vacant".
# Those strings leak into other cards' hidden headings exactly like the names
# do: District 11's card carries "District 12 - Vacant" as its third <h4>, and
# District 15's carries "District 16 - Vacant". A card-wide search for the word
# marks THREE live supervisors vacant. That is Chippewa's stale-notice trap in
# a different vendor's markup, and the answer is the same one: read the seat's
# own element, never the page around it.
#
# THE DISTRICT KEY IS WITNESSED BY THE COUNTY'S OWN MAILBOXES. Every filled
# seat's card carries districtN@ — district9@ on the card that says District 9,
# all seventeen — so the number is stated twice per card by two different
# mechanisms, and the builder requires them to agree. The four vacant seats
# publish no address, which is consistent: there is nobody to write to. Two
# domains are in use (@co.forest.wi.us and @co.forest.wi.gov, four seats on the
# latter); both are the county's and each ships as published.
#
# THE COMPOSITION NAMES MUNICIPALITIES WITHOUT SAYING WHAT THEY ARE, which is
# why ward_number_witness() learned to take a type of None. Forest writes
# "Argonne", "Hiles", "Popple River" bare and spells out only the one name that
# is two municipalities in this county — "Town of Crandon" and "City of
# Crandon". So the type is SUPPLIED BY LTSB rather than assumed: fourteen names,
# thirteen of which the state files under exactly one type. "Bare means town"
# would have been correct here and is still a guess; resolving it against the
# state's own filing is a measurement, and an ambiguous bare name resolves to
# nothing, strays, and fails the county rather than being picked.
#
# EACH MUNICIPALITY IS ITS OWN <p>, which is what makes this safe to read at
# all. "Argonne, Ward 1" and "Hiles" and "Lincoln, Ward 1" are three paragraphs,
# so there is no comma to guess about — one line is one municipality with an
# optional ward, and District 7's "Wabeno Ward 3" (no comma at all) parses the
# same way.
#
# EVERY SUPERVISOR'S HOME ADDRESS IS ON THIS PAGE AND NONE IS READ.
FOREST_CARDS = {
    "fips": "55041", "name": "Forest", "seats": 21,
    "source_url": "https://co.forest.wi.gov/county-board-supervisors",
}
FR_CARD = re.compile(r'(?is)<div data-ux="ContentCard"[^>]*>(.*?)'
                     r'(?=<div data-ux="GridCell"|<div data-ux="ContentCards"|\Z)')
FR_H4 = re.compile(r"(?is)<h4[^>]*>(.*?)</h4>")
FR_BODY = re.compile(r'(?is)<div data-ux="ContentCardText".*?>(.*?)</div>')
FR_P = re.compile(r"(?is)<p[^>]*>(.*?)</p>")
FR_DISTRICT = re.compile(r"(?i)^District\s*(\d+)$")
FR_VACANT = re.compile(r"(?i)^District\s*(\d+)\s*[-–]\s*Vacant$")
FR_MAIL = re.compile(r"(?i)mailto:\s*(district(\d+)@[A-Za-z0-9.-]+)")
FR_PHONE = re.compile(r"^\(?(\d{3})\)?[-.\s]?(\d{3})[-.\s](\d{4})$")
FR_ROLE = re.compile(r"\s*[-–]\s*((?:1st|2nd|3rd)?\s*(?:Vice\s*)?"
                     r"(?:County\s+Board\s+)?Chair(?:man|person|woman)?)\s*$", re.I)
FR_LINE = re.compile(r"(?i)^(?:(town|city|village)\s+of\s+)?(.+?)"
                     r"(?:\s*,?\s*wards?\s*(\d+))?$")
FR_TYPE = {"town": "t", "city": "c", "village": "v"}
FR_MIN_EMAILS = 15          # 17 of 17 filled seats today
FR_MIN_PHONES = 15          # 17 of 17
FR_MIN_WARD_PAIRS = 20      # 25 today, MEASURED: five districts are whole
                            # municipalities carrying no ward number at all
                            # (District 3 is Alvin, Caswell, Popple River and
                            # Ross entire). Barron's first floor was guessed
                            # from another county's document and failed a good
                            # build; this one is counted off the page.


def _fr_text(chunk):
    """One markup chunk as flat text."""
    return re.sub(r"\s+", " ", html_lib.unescape(
        re.sub(r"<[^>]+>", " ", chunk)).replace("\xa0", " ")).strip()


def scrape_forest_cards(spec):
    """All 21 seats or nothing, out of the county's own supervisors page."""
    county, seats = spec["name"], spec["seats"]
    page = fetch(spec["source_url"])
    cards = FR_CARD.findall(page)
    if not cards:
        raise RuntimeError("%s: no ContentCard blocks on %s — the county has "
                           "rebuilt its site; re-read the page"
                           % (county, spec["source_url"]))

    out, wards, munis, numbers = {}, {}, {}, {}
    for card in cards:
        heads = FR_H4.findall(card)
        if not heads:
            continue
        # h4[0] AND ONLY h4[0] — see the note above; the others are neighbours.
        head = _fr_text(heads[0])
        body = FR_BODY.search(card)
        if not body:
            raise RuntimeError("%s: a supervisor card carries no text block "
                               "(heading %r) — the card shape has changed"
                               % (county, head[:40]))
        lines = [x for x in (_fr_text(p) for p in FR_P.findall(body.group(1))) if x]
        at = [i for i, l in enumerate(lines) if FR_DISTRICT.match(l)]
        if len(at) != 1:
            raise RuntimeError("%s: a card states its district %d times (heading "
                               "%r) — one card, one district"
                               % (county, len(at), head[:40]))
        district = int(FR_DISTRICT.match(lines[at[0]]).group(1))
        if district in out:
            raise RuntimeError("%s: district %d appears on two cards" % (county, district))

        empty = FR_VACANT.match(head)
        if empty:
            # THE COUNTY'S OWN WORD, from this card's own heading. If it names
            # a different district than the card does, the leak described above
            # has reached h4[0] and nothing here is trustworthy.
            if int(empty.group(1)) != district:
                raise RuntimeError("%s: a card for district %d is headed %r — the "
                                   "hidden headings have displaced the real one"
                                   % (county, district, head))
            entry = {"name": None, "vacant": True, "role": None}
        else:
            role = None
            got = FR_ROLE.search(head)
            if got:
                role = re.sub(r"\s+", " ", got.group(1)).strip()
                head = FR_ROLE.sub("", head)
            name = clean(head)[0]
            if not is_name(name):
                raise RuntimeError("%s: district %d resolved the name %r — that is "
                                   "not a name, and the card has reshaped"
                                   % (county, district, name))
            entry = {"name": name, "vacant": False, "role": role}
            mail = FR_MAIL.search(card)
            if mail:
                # THE MAILBOX IS THE SECOND STATEMENT OF THE DISTRICT NUMBER.
                if int(mail.group(2)) != district:
                    raise RuntimeError("%s: the card that says District %d carries "
                                       "%s — the page states this seat's number "
                                       "two ways and they disagree"
                                       % (county, district, mail.group(1)))
                entry["email"] = mail.group(1).lower()
            for line in lines[:at[0]]:
                if FR_PHONE.match(line):
                    numbers[district] = ["-".join(FR_PHONE.match(line).groups())]
                    break
            # EVERY OTHER LINE BEFORE THE DISTRICT IS A HOME ADDRESS. Not read.

        w, m = set(), set()
        for line in lines[at[0] + 1:]:
            got = FR_LINE.match(line)
            if not got:
                continue
            ctv = FR_TYPE.get((got.group(1) or "").lower()) or None
            name = _jk_norm(got.group(2))
            if not name:
                continue
            m.add((ctv, name))
            if got.group(3):
                w.add((ctv, name, int(got.group(3))))
        if not m:
            raise RuntimeError("%s: district %d's card names no municipality — the "
                               "composition is what witnesses the numbering, so "
                               "this cannot ship unchecked" % (county, district))
        wards[district], munis[district] = w, m
        out[district] = entry

    seen = sorted(out)
    if seen != list(range(1, seats + 1)):
        raise RuntimeError("%s: the page lists districts %s, not 1..%d — re-read %s"
                           % (county, seen, seats, spec["source_url"]))

    drop_shared_phones(county, numbers, out)

    live = {d: r for d, r in out.items() if not r["vacant"]}
    names = [r["name"] for r in live.values()]
    if len(set(names)) != len(names):
        dupes = sorted({n for n in names if names.count(n) > 1})
        raise RuntimeError("%s: the same person is filed under two districts (%s) "
                           "— the hidden headings have displaced a real one"
                           % (county, dupes))

    emails = sum(1 for r in live.values() if r.get("email"))
    phones = sum(1 for r in live.values() if r.get("phone"))
    if emails < FR_MIN_EMAILS or phones < FR_MIN_PHONES:
        raise RuntimeError("%s: %d e-mails and %d phones across %d filled seats "
                           "(floors %d/%d) — the card body has reshaped and "
                           "contact is being dropped silently"
                           % (county, emails, phones, len(live),
                              FR_MIN_EMAILS, FR_MIN_PHONES))

    vacant = sorted(d for d, r in out.items() if r["vacant"])
    print("  %-12s %d seats, %d filled, %d phones, %d e-mails (no home address is "
          "read, and every filled card prints one)"
          % (county, seats, len(live), phones, emails), file=sys.stderr)
    if vacant:
        print("  note %-12s the county marks districts %s vacant, in the seat's own "
              "heading — those names leak into neighbouring cards' hidden "
              "headings, so the test is per heading and never per card"
              % (county, ", ".join(str(d) for d in vacant)), file=sys.stderr)
    print("  witness %-12s %d/%d filled seats carry the county's own "
          "district-keyed mailbox, each agreeing with its card's district number"
          % (county, emails, len(live)), file=sys.stderr)
    ward_number_witness(spec["fips"], county, wards, seats,
                        min_pairs=FR_MIN_WARD_PAIRS, munis=munis)
    roles = {d: r["role"] for d, r in out.items() if r.get("role")}
    rows = {str(d): dict(r) for d, r in out.items()}
    for r in rows.values():
        r.pop("role", None)
        r["role"] = None
    return attach_unique_roles(roles, rows, county), spec["source_url"]


# --- Waupaca: the Clerk's Directory of Public Officials, as a live page --------
#
# THE COUNTY BOARD'S OWN PAGE NAMES NOBODY. waupacacounty-wi.gov's
# /county_board/ carries four paragraphs about what a county board is and not
# one supervisor — zero "District n" anywhere on it — which is why Waupaca sat
# in the gap block. The county's own home page links "Directory of Public
# Officials" to public4.co.waupaca.wi.us/CountyDirectory, the Clerk's annual
# directory published as HTML rather than as the PDF Kenosha's Clerk uses, and
# its County Board Supervisors section is district-keyed for all 27 seats with a
# name, a phone and a county mailbox each. Same lesson as Jackson an hour
# earlier: ASK WHAT A COUNTY'S PAGES LINK, not only what they say.
#
# ITS HOST IS THE COUNTY'S OWN. public4.co.waupaca.wi.us is on co.waupaca.wi.us,
# the same domain every supervisor's mailbox sits on, and the county's home page
# is what links it — so this is the Clerk publishing, not a third party
# republishing.
#
# THE SHARED NUMBER IS THE COURTHOUSE AND IS DROPPED FROM ALL OF THEM. Districts
# 2, 3, 25 and 27 all print (715) 258-6200, which this same directory gives as
# the COUNTY CLERK's number ("Courthouse, Waupaca (715) 258-6200") and the
# county's own site prints in its footer. Those four supervisors publish no
# personal number and the directory falls back to the switchboard; shipping it
# would tell a reader they are calling their supervisor when they are calling
# the Clerk. The rule here is GENERIC rather than a pinned literal — a number
# that appears under more than one district is not one supervisor's, so it is
# dropped from every district that carries it and NAMED on the run log. That is
# Green Lake's shared-mailbox rule applied to phones, and it keeps working if
# the county changes its switchboard number.
#
# THREE SUPERVISORS PUBLISH TWO NUMBERS EACH (districts 4, 7 and 9). The first
# ships and the rest are named on the log, never dropped silently — again the
# Green Lake handling.
#
# TWO WITNESSES, BOTH INTERNAL TO THE DIRECTORY, AND BOTH GATED:
#   * every supervisor's name agrees with their own county mailbox
#     (duwayne.federwitz@ for DuWayne Federwitz), 27 of 27 today. This is the
#     Adams mailbox witness in a different shape, and it is what would catch a
#     block boundary that moved.
#   * the directory names its officers in a SEPARATE block above the listing
#     ("Chair - James Nygaard (District 9)", "Vice Chair - Ricky Ertl (District
#     7)") and that block states its own district numbers. They must match the
#     listing, which is a genuine anti-shift check: a reading that drifted by
#     one would put a different person at 9 and 7.
#
# THE HOME ADDRESSES ARE NOT CARRIED, as everywhere in this fleet.
WP_SECTION = 'id="county-board-supervisors"'
WP_SECTION_END = 'id="town-officials"'
WP_DIST = re.compile(r"^District\s+(\d{1,2})$")
WP_MAIL = re.compile(r"[\w.+-]+@co\.waupaca\.wi\.us", re.I)
WP_PHONE = re.compile(r"\(?(\d{3})\)?[\s.-]*(\d{3})[-.\s]*(\d{4})")
WP_OFFICER = re.compile(r"(Vice Chair|Chair)\s*[–—-]\s*([A-Za-z .'\-]+?)\s*"
                        r"\(District\s*(\d{1,2})\)")
WP_MIN_EMAILS = 25       # 27 of 27 publish one today
WP_MIN_AGREE = 25        # 27 of 27 names agree with their own mailbox today


def name_fold(text):
    """Letters only, lower-cased — for comparing a name against a mailbox."""
    return re.sub(r"[^a-z]", "", text.lower())


_wp_fold = name_fold          # the name it had while Waupaca was its only caller


def drop_shared_phones(county, numbers, rows):
    """A NUMBER ON MORE THAN ONE DISTRICT IS NOT A PERSONAL NUMBER.

    `numbers` is {district: [phone, ...]} in the order the page prints them;
    `rows` is the roster being built, keyed the same way. Every number that
    appears under two or more districts is dropped from ALL of them and named
    on the run log, and the first of whatever survives ships.

    THE RULE IS GENERIC RATHER THAN A PINNED LITERAL, and both counties that
    need it show why. Waupaca's districts 2, 3, 25 and 27 all print the
    COURTHOUSE switchboard, which its own directory gives as the County Clerk's
    number. St. Croix's districts 7, 10, 13 and 19 all print 715-386-4610,
    which that county's own staff directory gives as County Clerk Christine
    Hines's line. In both cases the supervisor publishes no personal number and
    the page falls back to a county office; shipping it would tell a reader
    they are calling their supervisor when they are calling the Clerk. Pinning
    either number would go stale the day a county changed it, and would say
    nothing about the next county to do the same thing.
    """
    shared = {p for p in {q for v in numbers.values() for q in v}
              if sum(1 for v in numbers.values() if p in v) > 1}
    for phone in sorted(shared):
        holders = sorted(d for d, v in numbers.items() if phone in v)
        print("  phone %-12s %s is published for districts %s — not one "
              "supervisor's, dropped from all"
              % (county, phone, ", ".join(str(d) for d in holders)), file=sys.stderr)
    for district, found in numbers.items():
        mine = [p for p in found if p not in shared]
        if not mine:
            continue
        rows[district]["phone"] = mine[0]
        if len(mine) > 1:
            print("  note %-12s district %d publishes %d numbers (%s) — the first "
                  "ships" % (county, district, len(mine), ", ".join(mine)),
                  file=sys.stderr)
    return shared


def scrape_directory_county(fips, county, seats, url):
    """All seats or nothing, out of the Clerk's own directory of officials."""
    page = fetch(url)
    start = page.find(WP_SECTION)
    if start < 0:
        raise RuntimeError("%s: no County Board Supervisors section on %s — the "
                           "Clerk's directory has reshaped; re-read it"
                           % (county, url))
    end = page.find(WP_SECTION_END, start)
    lines = _flat_lines(page[start:end if end > start else len(page)])

    heads = [(i, int(m.group(1)))
             for i, l in enumerate(lines) for m in [WP_DIST.match(l)] if m]
    seen = [d for _, d in heads]
    if sorted(seen) != list(range(1, seats + 1)):
        raise RuntimeError("%s: the directory's headings are %s, not 1..%d — "
                           "re-read %s" % (county, seen, seats, url))

    blocks, numbers = {}, {}
    for n, (i, district) in enumerate(heads):
        stop = heads[n + 1][0] if n + 1 < len(heads) else len(lines)
        block = lines[i + 1:stop]
        name = next((l for l in block if is_name(l)), None)
        if not name:
            raise RuntimeError("%s: district %d resolved no name from its block "
                               "(%r) — re-read %s" % (county, district, block[:4], url))
        found = []
        for line in block:
            for m in WP_PHONE.finditer(line):
                found.append("(%s) %s-%s" % m.groups())
        numbers[district] = found
        mail = next((m.group(0) for l in block for m in [WP_MAIL.search(l)] if m), None)
        blocks[district] = {"name": clean(name)[0], "vacant": False, "role": None}
        if mail:
            blocks[district]["email"] = mail

    # A NUMBER ON MORE THAN ONE DISTRICT IS NOT A PERSONAL NUMBER — see above.
    drop_shared_phones(county, numbers, blocks)

    names = [r["name"] for r in blocks.values()]
    if len(set(names)) != len(names):
        dupes = sorted({n for n in names if names.count(n) > 1})
        raise RuntimeError("%s: the same person is filed under two districts (%s) "
                           "— the block boundaries have moved" % (county, dupes))

    emails = sum(1 for r in blocks.values() if r.get("email"))
    agree = sum(1 for r in blocks.values() if r.get("email")
                and _wp_fold(r["name"].split()[-1]) in _wp_fold(r["email"].split("@")[0]))
    if emails < WP_MIN_EMAILS or agree < WP_MIN_AGREE:
        raise RuntimeError("%s: %d of %d seats carry a county mailbox and %d agree "
                           "with their own name (floors %d/%d) — the directory has "
                           "reshaped" % (county, emails, seats, agree,
                                         WP_MIN_EMAILS, WP_MIN_AGREE))
    print("  witness %-12s %d/%d supervisors' names agree with their own county "
          "mailbox" % (county, agree, seats), file=sys.stderr)

    # THE OFFICER BLOCK STATES ITS OWN DISTRICTS AND MUST AGREE WITH THE LISTING.
    officers = WP_OFFICER.findall(" \n".join(lines))
    if not officers:
        raise RuntimeError("%s: the directory names no chair or vice chair — that "
                           "block has moved; re-read %s" % (county, url))
    for role, who, district in officers:
        d = int(district)
        if d not in blocks:
            raise RuntimeError("%s: the officer block puts the %s in district %d, "
                               "which the listing does not carry" % (county, role, d))
        if _wp_fold(who) != _wp_fold(blocks[d]["name"]):
            raise RuntimeError(
                "%s: the officer block names %r as %s of district %d and the "
                "listing puts %r there — the two halves of one document disagree, "
                "which is what a shifted reading looks like"
                % (county, who.strip(), role, d, blocks[d]["name"]))
        blocks[d]["role"] = role_case(role)
        print("  role %-12s district %d: %s -> %s"
              % (county, d, blocks[d]["name"], role_case(role)), file=sys.stderr)
    return {str(d): r for d, r in blocks.items()}


# --- Door: a CivicPlus staff-directory widget per district ---------------------
#
# co.door.wi.gov/234/County-Board-of-Supervisors gives every district its own
# CivicPlus staff-directory widget, and the markup is the richest this file
# reads: an <h3> header naming the district, then a microformat card carrying
# the supervisor's name (p-name), their office (p-job-title), a county mailbox,
# a phone (p-tel) and a link to their own directory page (p-link).
#
# THE DISTRICT IS STATED THREE INDEPENDENT WAYS IN EVERY BLOCK and all three
# must agree, which is why this county needs no external witness. The widget
# header says "District 1"; the job title says "District 1 Supervisor and
# Chairperson"; the mailbox is district1@co.door.wi.gov. A reading that drifted,
# or a page that reshaped, breaks the agreement rather than shipping a plausible
# roster — and 21 of 21 agree today. That mailbox is the Adams witness exactly:
# a district-keyed address the county publishes, checked against the heading it
# sits under.
#
# THE PAGE IS TWO COLUMNS AND ITS DOCUMENT ORDER IS NOT 1..21. The odd districts
# run down the left (1, 3, 5 ... 21) and the evens down the right (2, 4 ... 20),
# so reading the document top to bottom yields 1, 3, 5, 7, 9, 11, 13, 15, 17,
# 19, 21, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20. NOTHING HERE READS BY POSITION —
# the district comes off each widget's own header — but an index-based or
# adjacency-based reading would scramble the board while resolving all 21 seats
# and passing every count guard, which is the failure this file keeps meeting in
# other shapes.
#
# THE ROLES SIT INSIDE THE JOB TITLE ("District 1 Supervisor and Chairperson"),
# not in a block of their own, and go through the same uniqueness gate every
# other structured county uses. "Supervisor" alone is an OFFICE and matches
# nothing — only the chair and vice chair carry a role here.
#
# THE PROFILE LINK SHIPS, unlike Calumet's. Door's p-link goes to
# /m/directory/employee?eid=N, a real per-supervisor page titled "Staff
# Directory - David Englebert"; the card renders that field as "Supervisor page"
# and this one is one. Calumet's equivalent was a contact FORM and was dropped
# for exactly that reason.
# EACH BLOCK IS BOUNDED BY ITS OWN <ol>, NOT BY THE NEXT WIDGET. Running a
# block to the next header instead makes the LAST one swallow the page footer:
# measured at 17 KB against a 1.2 KB typical block, and that footer carries a
# second county address (countyboard@co.door.wi.gov). Nothing shipped wrongly —
# the mailbox pattern below only matches districtN@ — but a block that extends
# past its own widget is a trap waiting for the day the footer changes, and the
# widget already states where it ends.
DOOR_WIDGET = re.compile(
    r'(?is)<div class="widgetHeader">.*?<h3>.*?>\s*District\s*(\d+)[^<]*</a>.*?</div>\s*'
    r'<ol class="semanticList">(.*?)</ol>')
# The CivicPlus h-card fields, shared by every county on that platform: Door
# gives each district its own widget, Oconto puts all 31 members in one. The
# FIELD names are the platform's and are identical; what differs is where the
# district is stated and what the u-email field actually points at, so those
# stay per county.
HCARD_ITEM = re.compile(r'(?is)<li class="widgetItem h-card">(.*?)</li>')
HCARD_NAME = re.compile(r'(?is)<h4[^>]*\bp-name\b[^>]*>(.*?)</h4>')
HCARD_TITLE = re.compile(r'(?is)class="field p-job-title"[^>]*>(.*?)</div>')
HCARD_TEL = re.compile(r'(?is)class="field p-tel"[^>]*>(.*?)</div>')
HCARD_LINK = re.compile(r'(?is)class="field p-link".*?href="([^"]+)"')
DOOR_MAIL = re.compile(r'mailto:(district(\d+)@co\.door\.wi\.gov)', re.I)
DOOR_PHONE = re.compile(r"\b(\d{3})[-.\s](\d{3})[-.\s](\d{4})\b")
DOOR_MIN_EMAILS = 19     # 21 of 21 today
DOOR_MIN_PHONES = 19     # 21 of 21 today


def scrape_staff_directory_county(fips, county, seats, url):
    """All seats or nothing, gated on the district's three statements agreeing."""
    page = fetch(url)
    found, vacant, contacts, roles = {}, set(), {}, {}
    for m in DOOR_WIDGET.finditer(page):
        district, body = int(m.group(1)), m.group(2)
        if not (1 <= district <= seats):
            continue
        name = HCARD_NAME.search(body)
        if not name:
            continue
        who = " ".join(html_lib.unescape(_TAG.sub(" ", name.group(1))).split())
        if VACANT.search(who):
            vacant.add(district)            # the county says the seat is empty
            continue
        if not is_name(who):
            raise RuntimeError("%s: district %d resolved %r, which does not read "
                               "as a name — re-read %s" % (county, district, who, url))
        title = HCARD_TITLE.search(body)
        office = " ".join(html_lib.unescape(_TAG.sub(" ", title.group(1))).split()) \
            if title else ""
        mail = DOOR_MAIL.search(body)
        # THE THREE STATEMENTS MUST AGREE — see the comment above.
        stated = re.match(r"District\s*(\d+)\b", office)
        if not stated or int(stated.group(1)) != district:
            raise RuntimeError(
                "%s: the widget header says district %d and the job title says "
                "%r — the page's own two statements of the district disagree, "
                "which is what a reshaped page looks like"
                % (county, district, office))
        if not mail or int(mail.group(2)) != district:
            raise RuntimeError(
                "%s: district %d carries the mailbox %r — the county's own "
                "district-keyed address disagrees with the heading it sits under"
                % (county, district, mail.group(1) if mail else None))
        found[district] = (clean(who)[0], None)
        row = {"email": mail.group(1).lower()}
        tel = HCARD_TEL.search(body)
        if tel:
            digits = DOOR_PHONE.search(
                " ".join(html_lib.unescape(_TAG.sub(" ", tel.group(1))).split()))
            if digits:
                row["phone"] = "-".join(digits.groups())
        link = HCARD_LINK.search(body)
        if link:
            row["url"] = urllib.parse.urljoin(url, html_lib.unescape(link.group(1)))
        contacts[district] = row
        # "Supervisor" is the office and matches nothing; only a chair does
        role = STRUCTURED_ROLE.search(office)
        if role:
            roles[district] = role_case(role.group(1))

    out = _resolve(county, seats, "staff-directory", found, vacant, contacts)
    emails = sum(1 for r in out.values() if r.get("email"))
    phones = sum(1 for r in out.values() if r.get("phone"))
    # the floors move with the board: a vacant seat carries no mailbox or phone,
    # and the message reports the floors actually applied rather than the
    # constants, so a run with a vacancy reads as the run it was
    want_mail = DOOR_MIN_EMAILS - len(vacant)
    want_tel = DOOR_MIN_PHONES - len(vacant)
    if emails < want_mail or phones < want_tel:
        raise RuntimeError("%s: %d e-mails and %d phones across %d seats (floors "
                           "%d/%d) — the directory widget has reshaped and contact "
                           "is being dropped silently"
                           % (county, emails, phones, seats, want_mail, want_tel))
    print("  witness %-12s %d/%d districts agree across the widget header, the job "
          "title and the county mailbox%s"
          % (county, len(found), seats,
             " (%d vacant)" % len(vacant) if vacant else ""), file=sys.stderr)
    return attach_unique_roles(roles, out, county)


# --- Oconto: the county this file called map-only for a year ------------------
#
# THE RECORD WAS WRONG AND ITS OWN CORRECTION SAID SO. This file's bullet list
# read "OCONTO publishes district MAPS - a page per district with a PDF and no
# name on it anywhere, re-checked 2026-08-29 and the record held", and two
# bullets later: "CHECK WHICH BOARD PAGE ... two slugs one word apart, one a map
# index and one the answer". Oconto is that sentence again. The directory table
# pointed at /307/County-Board-Supervisory-District-Maps, which is exactly the
# map index the record described; /453/County-Board names all 31 members with
# their districts and has all along.
#
# THE WORD IS "MEMBER", NOT "SUPERVISOR", AND THAT IS WHY THE SWEEP MISSED IT.
# The page contains the string "supervisor" ZERO times: every card reads "County
# Board Member, District 30". A sweep that greps for the office this project
# happens to call the job finds nothing on a page naming all 31 people. TEST FOR
# THE PEOPLE was the lesson written after Kenosha; testing for the WORD is how
# it fails.
#
# THE LIST IS ALPHABETICAL BY SURNAME, so document order is 30, 8, 26, 16, 12,
# 29, 31, 10, 5, 28, 3, ... Nothing here reads by position - the district comes
# out of each card's own job title - but an adjacency reading would scramble the
# whole board while resolving 31 seats.
#
# THE TWO OFFICERS BREAK A TITLE-KEYED READ, which is the Jackson (Illinois)
# trap in a new dress. Twenty-nine cards say "County Board Member, District N";
# district 6 says "County Board Vice Chair, District 6" and district 27 "County
# Board Chair, District 27". Keying on the literal "County Board Member" drops
# exactly the chair and the vice chair — a 29-seat board where 31 was expected,
# with the two most prominent members missing. The district is therefore taken
# from "District N" ANYWHERE in the title and the role from the same string.
#
# THE u-email FIELD IS A CONTACT FORM FOR 28 OF THE 31 and is not shipped as an
# address: /formcenter/County-Board-13/<name>-Contact-Form-89 is Calumet's case
# exactly. Three members do publish a real mailbox, district-keyed as
# cbdistrictN@ (on TWO county domains, co.oconto.wi.us and ocontocountywi.gov),
# and those three are checked against the district whose card they sit on — the
# Adams witness where it is available. The p-link, by contrast, IS a real page
# ("Staff Directory - Don Bartels Jr.") and ships as the supervisor page, which
# is the same distinction Door and Calumet already record.
#
# THE PHONES COME FROM THE PROFILE PAGES, because the list page carries none at
# all. That is the Manitowoc arrangement — a page per member, fetched and used
# as a witness — and the profile's own title must name the member the list page
# put on that district, or the fetch is discarded rather than trusted. THE
# COUNTY'S SWITCHBOARD SITS IN EVERY PROFILE'S FOOTER (920-834-6800, printed
# under the county's address), so a number found on more than one member is
# dropped from all of them: Waupaca's rule, and here it is the difference
# between 31 personal numbers and 31 copies of the courthouse.
OC_DIST = re.compile(r"(?i)\bDistrict\s*(\d+)\b")
OC_MAIL = re.compile(r"mailto:(cbdistrict(\d+)@(?:co\.oconto\.wi\.us|ocontocountywi\.gov))", re.I)
OC_PHONE = re.compile(r"\b(\d{3})[-.](\d{3})[-.](\d{4})\b")
OC_TITLE = re.compile(r"(?is)<title>(.*?)</title>")
OC_MIN_PHONES = 25       # 28 of 31 resolve one today; districts 9, 20 and 24
                         # publish no number of their own and ship without one
OC_MIN_LINKS = 29        # 31 of 31 today


def _oconto_profiles(cards, county, base):
    """{district: phone} from each member's own page, witnessed by its title."""
    phones, seen = {}, {}
    for district, (who, url) in sorted(cards.items()):
        try:
            page = fetch(urllib.parse.urljoin(base, url))
        except Exception as e:          # noqa: BLE001 - contact, never the roster
            print("  note %-12s district %d profile unreachable (%s) — no phone "
                  "this run" % (county, district, e), file=sys.stderr)
            continue
        title = OC_TITLE.search(page)
        named = html_lib.unescape(title.group(1)) if title else ""
        if _wp_fold(who) not in _wp_fold(named):
            # the page belongs to somebody else; a phone off it would be theirs
            print("  note %-12s district %d links a page titled %r, which does not "
                  "name %r — no phone taken" % (county, district, named.strip(), who),
                  file=sys.stderr)
            continue
        for m in OC_PHONE.finditer(page):
            seen.setdefault(district, []).append("-".join(m.groups()))
    # A NUMBER ON MORE THAN ONE MEMBER IS THE COUNTY'S, NOT THEIRS — see above.
    counts = {}
    for district, found in seen.items():
        for phone in set(found):
            counts[phone] = counts.get(phone, 0) + 1
    shared = {p for p, n in counts.items() if n > 1}
    for phone in sorted(shared):
        print("  phone %-12s %s appears on %d members — the county's, dropped from "
              "all" % (county, phone, counts[phone]), file=sys.stderr)
    for district, found in seen.items():
        mine = [p for p in found if p not in shared]
        if mine:
            phones[district] = mine[0]
    return phones


def scrape_member_cards_county(fips, county, seats, url):
    """All seats or nothing, out of one staff-directory widget of h-cards."""
    page = fetch(url)
    found, contacts, roles, links = {}, {}, {}, {}
    for m in HCARD_ITEM.finditer(page):
        body = m.group(1)
        name, title = HCARD_NAME.search(body), HCARD_TITLE.search(body)
        if not name or not title:
            continue
        who = " ".join(html_lib.unescape(_TAG.sub(" ", name.group(1))).split())
        office = " ".join(html_lib.unescape(_TAG.sub(" ", title.group(1))).split())
        stated = OC_DIST.search(office)
        if not stated:
            continue                    # a card on this page that is not a seat
        district = int(stated.group(1))
        if not (1 <= district <= seats) or district in found:
            continue
        if VACANT.search(who):
            continue                    # caught by the all-seats gate below
        if not is_name(who):
            raise RuntimeError("%s: district %d resolved %r, which does not read "
                               "as a name — re-read %s" % (county, district, who, url))
        found[district] = (clean(who)[0], None)
        row = {}
        mail = OC_MAIL.search(body)
        if mail:
            if int(mail.group(2)) != district:
                raise RuntimeError(
                    "%s: district %d carries the mailbox %r — the county's own "
                    "district-keyed address disagrees with the card it sits on"
                    % (county, district, mail.group(1)))
            row["email"] = mail.group(1).lower()
        link = HCARD_LINK.search(body)
        if link:
            href = html_lib.unescape(link.group(1))
            row["url"] = urllib.parse.urljoin(url, href)
            links[district] = (found[district][0], href)
        if row:
            contacts[district] = row
        role = STRUCTURED_ROLE.search(office)
        if role:
            roles[district] = role_case(role.group(1))

    if len(links) < OC_MIN_LINKS:
        raise RuntimeError("%s: only %d of %d cards link a member page (floor %d) "
                           "— the directory widget has reshaped; re-read %s"
                           % (county, len(links), seats, OC_MIN_LINKS, url))
    for district, phone in _oconto_profiles(links, county, url).items():
        contacts.setdefault(district, {})["phone"] = phone
    got = sum(1 for r in contacts.values() if r.get("phone"))
    if got < OC_MIN_PHONES:
        raise RuntimeError("%s: %d of %d members resolved a phone from their own "
                           "page (floor %d) — the profile pages have reshaped and "
                           "contact is being dropped silently"
                           % (county, got, seats, OC_MIN_PHONES))
    out = _resolve(county, seats, "member-cards", found, set(), contacts)
    return attach_unique_roles(roles, out, county)


def _ward_witness(fips, county, wards, seats):
    """The county's own ward composition against LTSB's ward-level SUPERID.

    A FETCH FAILURE IS NOT A DISAGREEMENT. An unreachable witness says nothing
    about the roster, so it prints and stands aside; a witness that RUNS and
    disagrees fails the county, because then the two publishers no longer
    number the same districts and the roster's district key is the thing in
    doubt.
    """
    try:
        data = _fetch_json(
            LTSB_WARD_QUERY + "?where=CNTY_FIPS%%3D%%27%s%%27&outFields="
            "MCD_NAME,CTV,WARDID,SUPERID&returnGeometry=false&f=json" % fips)
        feats = data.get("features") or []
        if not feats:
            raise RuntimeError("no wards returned")
    except Exception as e:      # noqa: BLE001 - the witness, never the source
        print("  WITNESS SKIPPED %-9s LTSB ward layer unreachable (%s) — the "
              "roster ships unwitnessed this run" % (county, e), file=sys.stderr)
        return
    ltsb = {}
    for f in feats:
        a = f.get("attributes") or {}
        key = (a.get("CTV"), re.sub(r"[^a-z]", "", str(a.get("MCD_NAME", "")).lower()),
               int(str(a.get("WARDID") or 0)))
        ltsb.setdefault(int(a["SUPERID"]), set()).add(key)
    placed = sum(len(v) for v in wards.values())
    if placed < 2 * seats:
        raise RuntimeError("%s: the page lists only %d wards across %d districts — "
                           "it has stopped printing its ward composition, and the "
                           "numbering witness with it" % (county, placed, seats))
    hit = sum(len(v & ltsb.get(d, set())) for d, v in wards.items())
    shifts = [sum(len(v & ltsb.get(d + off, set())) for d, v in wards.items())
              for off in (1, -1)]
    print("  witness %-12s %d/%d listed wards in LTSB's own district (shifts %d/%d)"
          % (county, hit, placed, shifts[0], shifts[1]), file=sys.stderr)
    # THE SHIFT TEST IS COMPARATIVE, NOT ABSOLUTE. It asks whether the county's
    # numbering fits LTSB's file BETTER at its own offset than one district
    # along, which is the shape a renumbering takes. It was written as "any
    # shifted match at all fails", which is true of Jackson's document and false
    # in general: Clark scores a perfect 56/56 at its own offset and still picks
    # up 1 and 2 stray hits shifted, because two neighbouring districts happen
    # to contain a like-numbered ward in different municipalities. Refusing a
    # county on 2 coincidences against 56 exact matches would reject a roster
    # that agrees with the state completely. A real renumbering inverts the
    # ratio — the shift scores near everything and the true offset near nothing.
    if hit and max(shifts) > 0.5 * hit:
        raise RuntimeError("%s: %d of its listed wards land in LTSB's "
                           "same-numbered district but %d land one district off "
                           "— too close to call, and the two publishers may have "
                           "renumbered apart; re-read both before shipping"
                           % (county, hit, max(shifts)))
    if not hit and any(shifts):
        raise RuntimeError("%s: NONE of its listed wards land in LTSB's "
                           "same-numbered district and %d land one off — the "
                           "document is numbered against a different plan"
                           % (county, max(shifts)))
    if hit < 0.95 * placed:
        raise RuntimeError("%s: only %d of %d listed wards land in LTSB's "
                           "same-numbered district — the county's composition and "
                           "the state's filing no longer describe one plan"
                           % (county, hit, placed))


def scrape_fielded_county(fips, county, seats, url):
    """All seats or nothing, then the witnesses — see FIELDED_PINS above."""
    lines = to_lines(fetch(url))
    found, vacant, wards = _fielded(lines)
    covered = set(found) | vacant
    if covered != set(range(1, seats + 1)):
        missing = sorted(set(range(1, seats + 1)) - covered)
        raise RuntimeError(
            "%s: resolved %d of %d districts (missing %s) under the 'fielded' "
            "reading — the page has changed shape; re-read it before moving this "
            "entry" % (county, len(covered), seats, missing))
    pins = FIELDED_PINS.get(fips, {})
    for d, (was, now) in sorted(pins.get("name_fixes", {}).items()):
        if found.get(d, {}).get("name") != was:
            raise RuntimeError(
                "%s: district %s no longer prints %r (it prints %r) — the pinned "
                "correction to %r has been overtaken by the county; delete it"
                % (county, d, was, found.get(d, {}).get("name"), now))
        found[d]["name"] = now
        print("  name %-12s district %s: %r -> %r (the county's own e-mail and "
              "the Clerk's filing list)" % (county, d, was, now), file=sys.stderr)
    names = [r["name"] for r in found.values()]
    if len(set(names)) != len(names):
        dupes = sorted({n for n in names if names.count(n) > 1})
        raise RuntimeError("%s: the same person is filed under two districts (%s)"
                           % (county, dupes))
    for d in sorted(found):
        if not _email_agrees(found[d]["name"], found[d]["email"]):
            raise RuntimeError(
                "%s: district %s pairs %r with %r — the county builds its "
                "mailboxes from its supervisors' own names, so a row whose "
                "e-mail names somebody else is the shift this reading exists to "
                "rule out" % (county, d, found[d]["name"], found[d]["email"]))
    shared = {}
    for d in sorted(found):
        shared.setdefault(digits(found[d]["phone"]), []).append(d)
    owner = pins.get("phone_owner", {})
    for num in sorted(owner):
        # the same rule the name pin follows: a pin that no longer describes
        # the page is deleted, never left standing as a fact nobody rechecks
        if len(shared.get(num, [])) < 2:
            raise RuntimeError(
                "%s: %s is no longer published for two districts — the pinned "
                "owner (district %s) has been overtaken by the county; delete it"
                % (county, num, owner[num]))
    for num, seats_sharing in sorted(shared.items()):
        if not num or len(seats_sharing) == 1:
            continue
        for d in seats_sharing:
            if owner.get(num) == d:
                continue
            print("  phone %-12s district %s: withheld — %s is published for "
                  "districts %s and cannot be all of theirs"
                  % (county, d, found[d]["phone"],
                     ", ".join(str(x) for x in seats_sharing)), file=sys.stderr)
            found[d]["phone"] = None
    _ward_witness(fips, county, wards, seats)
    out = {}
    for d in range(1, seats + 1):
        if d in vacant:
            out[str(d)] = {"name": None, "vacant": True, "role": None}
            continue
        row = {"name": found[d]["name"], "vacant": False, "role": found[d]["role"]}
        if found[d]["email"]:
            row["email"] = found[d]["email"]
        if found[d]["phone"]:
            row["phone"] = found[d]["phone"]
        out[str(d)] = row
    return out
# --- COUNTIES THAT LINK A PAGE PER SUPERVISOR ---------------------------------
# Manitowoc, and so far only Manitowoc. Every row of its list is an anchor whose
# href is that supervisor's own personnel page, so the district and the link
# arrive TOGETHER — nothing is matched up by position, which is what makes
# fetching twenty-five more pages a safe thing to do rather than a second place
# for a roster to shift by one.
#
# What the personnel page adds: a second statement of the district (a tripwire,
# not the source — see the docstring), a county e-mail, the page itself as
# `profileUrl`, and the person's own job title, which is where a chair would be
# labelled if the county ever labelled one. What it deliberately does NOT add is
# the home address and home telephone printed beside them.
PROFILE_COUNTIES = {"55071"}                    # Manitowoc
PROFILE_ROW = re.compile(r'<a\s[^>]*href="([^"]+)"[^>]*>\s*(\d{1,2})\s+([^<]+?)\s*</a>')
# the supervisor's OWN block: a page-wide <h1>/<h2> search would read a banner
# heading as somebody's name or title
PROFILE_BLOCK = re.compile(r'(?is)<article[^>]*class="[^"]*team-member[^"]*"[^>]*>(.*?)</article>')
PROFILE_DISTRICT = re.compile(r"(?i)Supervisory\s+District:\s*(\d{1,2})")
PROFILE_NAME = re.compile(r"(?is)<h1[^>]*>\s*(.*?)\s*</h1>")
PROFILE_TITLE = re.compile(r"(?is)<h2[^>]*>\s*(.*?)\s*</h2>")
# Of 25. FALLING BELOW THIS PRINTS A NOTE AND DOES NOT FAIL THE COUNTY, and the
# asymmetry is deliberate: the names come from the LIST page, which has its own
# all-seats-or-nothing guard, so failing Manitowoc because its personnel pages
# stopped carrying an e-mail would delete twenty-five supervisors from the card
# over a CONTACT field. A field that stops being published is exactly what
# check_roster_retention.py measures, and it fails the weekly PR — a human look
# — rather than dropping the county. What DOES fail here is the pair of things
# that would otherwise be silent and wrong: a personnel page naming a different
# district than the list, and obfuscation markup that decodes to nothing.
PROFILE_MIN = 20
CFEMAIL = re.compile(r'data-cfemail="([0-9a-fA-F]{4,})"')
EMAIL_SHAPE = re.compile(r"^[a-z0-9][a-z0-9._%+-]*@[a-z0-9][a-z0-9.-]*\.[a-z]{2,}$", re.I)
# The site's own scramble, undone in every visitor's browser by the handler on
# the class="replace-html-with-email" links: the 36-character alphabet reversed.
# It is an involution, so this function is its own inverse. Case is CARRIED
# rather than folded — every Manitowoc address is lower-case today, and
# lower-casing one that is not would be this project rewriting somebody's
# contact detail.
SCRAMBLE_ALPHABET = "abcdefghijklmnopqrstuvwxyz0123456789"


def cf_decode(token):
    """Cloudflare's e-mail obfuscation: first byte is the XOR key."""
    raw = bytes.fromhex(token)
    return "".join(chr(c ^ raw[0]) for c in raw[1:])


def unscramble(text):
    out = []
    for ch in text:
        i = SCRAMBLE_ALPHABET.find(ch.lower())
        if i < 0:
            out.append(ch)                  # "@", ".", "-" and friends pass through
            continue
        mapped = SCRAMBLE_ALPHABET[len(SCRAMBLE_ALPHABET) - 1 - i]
        out.append(mapped.upper() if ch.isupper() else mapped)
    return "".join(out)


def profile_email(page_html):
    """(address_or_None, whether the obfuscation markup was there at all).

    Two layers, both the page's own and both run in every visitor's browser;
    see the docstring for why decoding them is reading a published address and
    not defeating an access control. Markup present and nothing decoded is a
    hard failure at the call site — that is the exact way Brown County's seven
    addresses went silently empty.
    """
    m = CFEMAIL.search(page_html or "")
    if not m:
        return None, False
    try:
        address = unscramble(cf_decode(m.group(1))).strip()
    except ValueError:
        return None, True
    return (address if EMAIL_SHAPE.match(address) else None), True


def _surname(person):
    toks = [t for t in re.split(r"[^A-Za-z]+", person or "") if len(t) > 1]
    return toks[-1].lower() if toks else ""


def attach_profiles(page, list_url, districts, county):
    """Add e-mail, profileUrl and the county's own job title from each
    supervisor's personnel page, and fail loudly if it names another district."""
    links = {}
    for href, num, label in PROFILE_ROW.findall(page):
        d = str(int(num))
        row = districts.get(d)
        if not row or not row.get("name") or d in links:
            continue
        # the anchor must be the row this reading already produced, or it is
        # some other numbered link on the page and is none of our business
        if _surname(clean(html_lib.unescape(label))[0]) == _surname(row["name"]):
            links[d] = urllib.parse.urljoin(list_url, href)
    seen = {"district": 0, "email": 0, "markup": 0, "title": 0}
    for n, d in enumerate(sorted(links, key=int)):
        row = districts[d]
        if n:
            time.sleep(0.5)         # 25 pages of somebody else's server
        try:
            profile = fetch(links[d])
        except Exception as e:      # noqa: BLE001 - one page never fails the county
            print("  note %-12s district %s: profile page unreadable (%s)"
                  % (county, d, e), file=sys.stderr)
            continue
        block = PROFILE_BLOCK.search(profile)
        block = block.group(1) if block else ""
        m = PROFILE_DISTRICT.search(block or profile)
        if m:
            seen["district"] += 1
            if int(m.group(1)) != int(d):
                raise RuntimeError(
                    "%s: the list files %s under district %s and their own page "
                    "says district %s — the two county surfaces disagree, ship "
                    "neither" % (county, row["name"], d, m.group(1)))
        who = PROFILE_NAME.search(block)
        if who:
            page_name = " ".join(_TAG.sub(" ", who.group(1)).split())
            if _surname(page_name) != _surname(row["name"]):
                raise RuntimeError(
                    "%s: district %s links a page for %r, not %r"
                    % (county, d, page_name, row["name"]))
        title = PROFILE_TITLE.search(block)
        if title:
            stated = split_role(" ".join(_TAG.sub(" ", title.group(1)).split()))[1]
            if stated and not row.get("role"):
                row["role"] = stated
                seen["title"] += 1
                print("  role %-12s district %s: %s -> %s (their own page)"
                      % (county, d, row["name"], stated), file=sys.stderr)
        # the district is looked for page-wide because a wrong one FAILS, but
        # the address is read from this supervisor's own block ONLY: a
        # page-wide search would happily ship a footer's webmaster address as
        # somebody's contact, and a block that stops matching should empty the
        # column for the retention gate to catch, never fill it with a guess.
        address, markup = profile_email(block)
        seen["markup"] += 1 if markup else 0
        if address:
            row["email"] = address
            seen["email"] += 1
        row["url"] = links[d]
    if seen["markup"] and not seen["email"]:
        raise RuntimeError(
            "%s: %d personnel pages carry the e-mail obfuscation markup and not "
            "one address decoded — the encoding has changed; a silently empty "
            "contact column is the failure this check exists for"
            % (county, seen["markup"]))
    for field in ("district", "email"):
        if seen[field] < PROFILE_MIN:
            print("  note %-12s only %d of %d personnel pages state a %s — the "
                  "county still ships on its list page; retention gates the field"
                  % (county, seen[field], len(links), field), file=sys.stderr)
    print("  prof %-12s %d pages: %d districts witnessed, %d e-mails, %d titled"
          % (county, len(links), seen["district"], seen["email"], seen["title"]),
          file=sys.stderr)
    return districts


def scrape_county(fips, name, seats, strategy, url):
    """All seats or nothing — see the module docstring."""
    if strategy == "member-cards":
        # One staff-directory widget of h-cards, alphabetical by surname, the
        # district stated only inside each card's job title. Phones come from
        # each member's own page — see `scrape_member_cards_county`.
        return scrape_member_cards_county(fips, name, seats, url), "live"
    if strategy == "staff-directory":
        # A CivicPlus staff-directory widget per district, whose block states the
        # district three ways — header, job title and county mailbox — and is
        # gated on all three agreeing.
        return scrape_staff_directory_county(fips, name, seats, url), "live"
    if strategy == "directory":
        # The board's own page names nobody; the Clerk's directory of public
        # officials does, district-keyed, on the county's own host.
        return scrape_directory_county(fips, name, seats, url), "live"
    if strategy == "pdf-roster":
        # The county's HTML names nobody; its listing page links a district-keyed
        # roster PDF, discovered fresh each run because the filename carries the
        # board's term. Returns the document it read so the row can cite it.
        districts, doc = scrape_pdf_roster_county(fips, name, seats, url)
        return districts, "live", doc
    if strategy == "fielded":
        # Sauk's page names no district NEAR a name; it labels its own fields,
        # so the whole page is read at once rather than as a line list.
        return scrape_fielded_county(fips, name, seats, url), "live"
    page_html, read_from = fetch_or_archive(url, fips, name, headers_for(url))
    if strategy == "heading-block":
        # A name heading paired with a district heading, per supervisor. Its
        # roles come back separately for the same uniqueness gate `cells` uses.
        found, vacant, contacts, roles = _heading_block(page_html, seats)
        out = _resolve(name, seats, strategy, found, vacant, contacts)
        got = sum(1 for r in out.values() if r.get("email"))
        if got < EMAIL_MIN:
            # Cloudflare obfuscation that decodes to nothing is a HARD failure,
            # never a quietly empty column — the Brown County (IL) rule.
            raise RuntimeError(
                "%s: %d of %d seats resolved an e-mail, floor is %d — the page's "
                "obfuscation has changed and the addresses are being dropped "
                "silently" % (name, got, seats, EMAIL_MIN))
        return attach_unique_roles(roles, out, name), read_from
    if strategy == "cells":
        # A district per TABLE CELL: the cell boundary is the guard, so this
        # never walks into a neighbouring district the way a line reading can.
        # Its roles come back separately because the page contradicts itself on
        # one of them — see the `_calumet` comment.
        found, vacant, contacts, roles = _calumet(page_html, seats)
        out = _resolve(name, seats, strategy, found, vacant, contacts)
        return attach_unique_roles(roles, out, name), read_from
    if strategy == "indexroll":
        # A structured page carries the role in the person's own block, so it
        # needs no `attach_officer_roles` pass over the flattened lines — and
        # must not have one: that pass reads by adjacency, which is exactly the
        # inference this shape removes.
        found, vacant, contacts = _indexroll(page_html, seats)
        return _resolve(name, seats, strategy, found, vacant, contacts), read_from
    lines = to_lines(page_html)
    contacts = {}
    if strategy == "row":
        found, vacant = _rows(page_html, seats)
    elif strategy == "table":
        # the table reader works on the MARKUP: its whole point is that the
        # row boundaries the lines threw away are what makes the page safe
        found, vacant, contacts = _monroe(page_html)
    elif strategy in STRICT_READINGS:
        found, vacant = STRICT_READINGS[strategy](lines)
    elif strategy == "numbered-line":
        found, vacant = _numbered_line(lines, seats)
    elif strategy in COLUMN_READINGS:
        # A column page names no district beside a seat, so `vacant_districts`
        # (which keys off the WORD) can never see its vacancies; the column
        # reader reports them from the cell it actually lands on instead.
        found, vacant = _column(lines, seats, COLUMN_READINGS[strategy])
    else:
        vacant = vacant_districts(lines, seats, strategy)
        found = READINGS[strategy](lines)
    # Marinette's unnumbered vacancy needs the flattened LINES, which only the
    # line-based readings have, so it rides in as a callback rather than as two
    # more parameters a structured page would have to pass None for.
    eliminate = None
    if fips in ELIMINATION_VACANCY:
        eliminate = lambda f, v: eliminated_vacancy(lines, seats, f, v, name)  # noqa: E731
    out = _resolve(name, seats, strategy, found, vacant, contacts, eliminate)
    if fips in PROFILE_COUNTIES:
        # Manitowoc links a page per supervisor; the contact it publishes lives
        # there and nowhere on the list page.
        attach_profiles(page_html, url, out, name)
    if fips in MEMBER_PAGES:
        out = member_pages(MEMBER_PAGES[fips], out, name)
    if strategy == "same-line-lead":
        # Lafayette names its officers "Name, Role" in a block above the seat
        # list; the "Role - Name" reader below cannot see that shape.
        return attach_named_officer_roles(lines, out, name), read_from
    officers = OFFICER_PAGES.get(fips)
    if officers:
        # the county states its officers somewhere other than the page its
        # district list came from, so the officer scan takes THAT page and the
        # row records where the role was read
        return attach_officer_roles(
            to_lines(fetch(officers["url"], headers_for(officers["url"]))),
            out, name, officers.get("name_side"),
            OFFICER_LINE_BY_COUNTY.get(fips, OFFICER_LINE), officers["url"]), read_from
    return attach_officer_roles(lines, out, name, OFFICER_NAME_SIDE.get(fips),
                                OFFICER_LINE_BY_COUNTY.get(fips, OFFICER_LINE)), read_from


def _resolve(name, seats, strategy, found, vacant, contacts, eliminate=None):
    """The gates every reading answers to: all seats, and no one twice."""
    for d in vacant:
        found.pop(d, None)          # the county says the seat is empty; believe it
    if eliminate:
        d = eliminate(found, vacant)
        if d is not None:
            vacant.add(d)
    covered = set(found) | vacant
    if covered != set(range(1, seats + 1)):
        missing = sorted(set(range(1, seats + 1)) - covered)
        raise RuntimeError(
            "%s: resolved %d of %d districts (missing %s) under the pinned '%s' "
            "reading — the page has changed shape; re-read it before moving this "
            "entry" % (name, len(covered), seats, missing, strategy))
    names = [v[0] for v in found.values()]
    if len(set(names)) != len(names):
        dupes = sorted({n for n in names if names.count(n) > 1})
        raise RuntimeError("%s: the same person is filed under two districts (%s) — "
                           "a sign the reading direction has shifted" % (name, dupes))
    out = {}
    for d in range(1, seats + 1):
        if d in vacant:
            out[str(d)] = {"name": None, "vacant": True, "role": None}
        else:
            member, role = found[d]
            row = {"name": member, "vacant": False, "role": role}
            row.update(contacts.get(d, {}))
            out[str(d)] = row
    return out

# EVERY CARRIER THAT SERVES EXACTLY ONE COUNTY, IN ONE PLACE. These used to be
# three hand-written `jobs +=` lines and a literal `+ 3` in the run summary's
# arithmetic, which is the same hand-kept-list defect wi/scripts/validate_robots.py
# was carrying one file over: adding a fourth meant remembering to bump a number
# nothing checks, and a summary that under-counts reads as counties silently
# missing. The list is the count now.
SINGLE_COUNTY_CARRIERS = (
    (CLARK_DIRECTORY, "official-directory"),
    (PIERCE_DIRECTORY, "pierce-directory"),
    (MARATHON_DIRECTORY, "marathon-directory"),
    (ST_CROIX_TABLE, "st-croix-table"),
    (CHIPPEWA_DIRECTORY, "chippewa-directory"),
    (MENOMINEE_BOARD, "menominee-board"),
    (LANGLADE_BOARD, "langlade-board"),
    (BARRON_TABLE, "barron-table"),
    (FOREST_CARDS, "forest-cards"),
    (FLORENCE_BOARD, "florence-board"),
    (SAWYER_DIRECTORY, "sawyer-directory"),
    (DOUGLAS_TABLE, "douglas-table"),
    (IRON_BOARD, "iron-board"),
)


def main():
    argv = sys.argv[1:]
    out_path = argv[argv.index("--out") + 1] if "--out" in argv else DEFAULT_OUT
    only = argv[argv.index("--only") + 1] if "--only" in argv else None
    scraped_at = os.environ.get("SCRAPED_AT") or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    counties, failures = {}, []
    jobs = [(c["fips"], c["name"], c["seats"], "arcgis", c) for c in ARCGIS_COUNTIES]
    jobs += [(a["fips"], a["name"], a["seats"], "archive", a) for a in ARCHIVE_COUNTIES]
    jobs += [(d["fips"], d["name"], d["seats"], "document", d) for d in DOCUMENT_ROSTERS]
    jobs += [(c["fips"], c["name"], c["seats"], "constituent", c) for c in CONSTITUENT_COUNTIES]
    jobs += [(c["fips"], c["name"], c["seats"], "witnessed-document", c)
             for c in WITNESSED_DOCUMENT_COUNTIES]
    jobs += [(d["fips"], d["name"], d["seats"], "pdf", d) for d in PDF_COUNTIES]
    jobs += [(t["fips"], t["name"], t["seats"], "framed-table", t)
             for t in FRAMED_TABLE_COUNTIES]
    jobs += [(spec["fips"], spec["name"], spec["seats"], strategy, spec)
             for spec, strategy in SINGLE_COUNTY_CARRIERS]
    jobs += [(fips, name, seats, strategy, url) for fips, name, seats, strategy, url in COUNTIES]
    for fips, name, seats, strategy, src in jobs:
        if only and fips != only:
            continue
        carried = False
        try:
            archived_at = None
            doc_url = None
            at_large = None
            if strategy == "arcgis":
                districts = scrape_arcgis_county(src)
                source_url, read_from = src["source_url"], "live"
            elif strategy == "official-directory":
                districts, doc_url = scrape_official_directory_county(src)
                source_url, read_from = src["source_url"], "live"
            elif strategy == "pierce-directory":
                districts, doc_url = scrape_pierce_directory(src)
                source_url, read_from = src["source_url"], "live"
            elif strategy == "marathon-directory":
                districts, _doc = scrape_marathon_directory(src)
                source_url, read_from = src["source_url"], "live"
            elif strategy == "st-croix-table":
                districts, _doc = scrape_st_croix_table(src)
                source_url, read_from = src["source_url"], "live"
            elif strategy == "chippewa-directory":
                districts, _doc = scrape_chippewa_directory(src)
                source_url, read_from = src["source_url"], "live"
            elif strategy == "menominee-board":
                districts, at_large, _doc = scrape_menominee_board(src)
                source_url, read_from = src["source_url"], "live"
            elif strategy == "langlade-board":
                districts, _doc = scrape_langlade_board(src)
                source_url, read_from = src["source_url"], "live"
            elif strategy == "barron-table":
                districts, _doc = scrape_barron_table(src)
                source_url, read_from = src["source_url"], "live"
            elif strategy == "forest-cards":
                districts, _doc = scrape_forest_cards(src)
                source_url, read_from = src["source_url"], "live"
            elif strategy == "florence-board":
                districts, _doc = scrape_florence_board(src)
                source_url, read_from = src["source_url"], "live"
            elif strategy == "sawyer-directory":
                districts, _doc = scrape_sawyer_directory(src)
                source_url, read_from = src["source_url"], "live"
            elif strategy == "douglas-table":
                districts, _doc = scrape_douglas_table(src)
                source_url, read_from = src["source_url"], "live"
            elif strategy == "iron-board":
                districts, _doc = scrape_iron_board(src)
                source_url, read_from = src["source_url"], "live"
            elif strategy == "archive":
                districts, archived_at = scrape_archive_county(src)
                source_url = src["source_url"]
                # One capture timestamp per directory page read, and None
                # where the COUNTY served that page itself. All-None is the
                # good case — the block lifted — so it reads as the live read
                # it was rather than as an archive hop with no date.
                stamps = [t for t in (archived_at or []) if t]
                read_from = "archive:" + max(stamps) if stamps else "live"
            elif strategy == "document":
                districts, carried = document_county(src)
                source_url = src["source_url"]
                # a document county whose live page answered this run was read
                # live, and the log has to say which it was
                read_from = "document" if carried else "live"
            elif strategy == "constituent":
                districts = scrape_constituent_county(src)
                source_url, read_from = src["source_url"], "live"
            elif strategy == "witnessed-document":
                districts = scrape_witnessed_document(src)
                source_url, read_from = src["source_url"], "live"
            elif strategy == "pdf":
                districts, doc_url = scrape_pdf_county(src)
                source_url, read_from = src["source_url"], "live"
            elif strategy == "framed-table":
                districts = scrape_framed_table_county(src)
                source_url, read_from = src["page"], "live"
            else:
                got = scrape_county(fips, name, seats, strategy, src)
                if len(got) == 3:
                    # a strategy that reads a linked DOCUMENT reports which one
                    districts, read_from, doc_url = got
                else:
                    districts, read_from = got
                source_url = src
        except Exception as e:      # noqa: BLE001 - one county never fails the run
            failures.append("%s (%s): %s" % (name, fips, e))
            print("  MISS %-12s %s" % (name, e), file=sys.stderr)
            continue
        counties[fips] = {"county": name, "seats": seats, "source_url": source_url,
                          "scraped_at": scraped_at, "read_from": read_from,
                          "districts": districts}
        # THE SUPERVISORS WHO HOLD NO DISTRICT. Only Menominee has any, and
        # they are carried beside the districts rather than inside them: a
        # district-keyed roster has no slot for a member elected countywide,
        # and dropping them would ship a five-member board for a seven-member
        # body with the Vice-Chair among the missing.
        if at_large:
            counties[fips]["at_large"] = at_large
        if strategy in ("pdf", "pdf-roster"):
            # the roster IS re-read every run — the edition it was read from is
            # recorded so a reader of the JSON can see which one answered
            counties[fips]["document_url"] = doc_url
        if carried:
            # the file must SAY the roster was not re-read this run; a reader
            # of the JSON should never have to know which table it came from.
            # Keyed off the RESULT rather than the table, so a county whose
            # live page answered this run ships as the live read it was.
            counties[fips]["carried_from_document"] = True
            counties[fips]["read_on"] = src["read_on"]
            counties[fips]["how"] = src["how"]
            # The document that NAMES the members, where the source_url page
            # does not — Jackson's HTML names nobody and its roster is a PDF,
            # so a reader sent only to the page has nothing to check against.
            if src.get("document_url"):
                counties[fips]["document_url"] = src["document_url"]
            # a county whose reason differs from the card's default says so
            if src.get("why"):
                counties[fips]["why"] = src["why"]
        if strategy == "archive" and any(archived_at or []):
            # SAME PRINCIPLE AS THE DOCUMENT LINE ABOVE: the file records that
            # this county's page was read through a public archive and WHEN
            # each copy was taken, so nobody has to know which table it came
            # from to know how fresh it is. A page the county served directly
            # carries no stamp, which is how a lifted block shows up here.
            counties[fips]["read_via_archive"] = True
            counties[fips]["archived_at"] = archived_at
        vac = sum(1 for d in districts.values() if d["vacant"])
        print("  ok   %-12s %d seats%s%s"
              % (name, seats, " (%d vacant)" % vac if vac else "",
                 "" if read_from in ("live", "document") else " [%s]" % read_from),
              file=sys.stderr)

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump({"counties": counties, "failures": failures}, f, indent=2, ensure_ascii=False)
    total = sum(c["seats"] for c in counties.values())
    print("wrote %s: %d/%d counties, %d seats%s"
          % (out_path, len(counties),
             len(COUNTIES) + len(ARCGIS_COUNTIES) + len(DOCUMENT_ROSTERS)
             + len(ARCHIVE_COUNTIES)
             + len(CONSTITUENT_COUNTIES)
             + len(WITNESSED_DOCUMENT_COUNTIES)
             + len(PDF_COUNTIES)
             + len(FRAMED_TABLE_COUNTIES) + len(SINGLE_COUNTY_CARRIERS), total,
             ", %d county/counties missed" % len(failures) if failures else ""),
          file=sys.stderr)


if __name__ == "__main__":
    main()
