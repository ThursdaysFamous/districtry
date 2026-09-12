#!/usr/bin/env python3
"""
Build data/app/county-board-directory.json — one row per Wisconsin county
naming its board's size and its own official page, so the supervisory-district
card can send a reader to the body that answers for them.

WHY THIS FILE EXISTS SEPARATELY FROM THE GEOMETRY
--------------------------------------------------
The districts come from one statewide publisher (LTSB). The PEOPLE do not:
Wisconsin has no statewide roster of county supervisors, so a reader's actual
supervisor is only ever published by their own county, 72 different ways. The
honesty rules say a card with no verifiable roster source links to the
official body rather than inventing a name, and this file is that link — one
verified URL per county, with the county's board size beside it.

It is also where a roster would land when one is built, which is why it is
keyed by county FIPS and shaped like the fleet's other roster files rather
than being folded into the geometry's properties.

WHERE THE URLS CAME FROM, AND WHY THEY ARE CURATED RATHER THAN DERIVED
----------------------------------------------------------------------
LTSB's district layer carries a CONTACT e-mail per county, which looks like a
free county-domain list and is not one. Five counties contract their GIS out,
so their contact is an ENGINEERING FIRM — Florence's is coleman-engineering
.com, Juneau's ncwrpc.org, Kewaunee's ruekert-mielke.com, Price's mi-tech.us,
Richland's msa-ps.com — and a card built from that list would have sent five
counties' readers to a consultancy captioned as their county board. Four more
contact domains host no website at all: Columbia, Crawford and Sauk are
MAIL-ONLY (no A record, live MX) and Iron's serves a certificate for another
name and 404s. Every URL below was fetched, and `--probe` re-fetches them on
demand: most answer 200, a dozen answer 403 to a datacenter client while
serving browsers normally, a few refuse this client outright, and Taylor sits
behind an sgcaptcha challenge that a person passes and no automation here
tries to. Those tallies are deliberately not written down as numbers — they
move with the counties' hosting and with whichever network runs the probe, and
a hand-kept count in a comment is how a record starts lying.

A 200 IS NOT PROOF THE COUNTY IS STILL THERE (measured 2026-08-29)
------------------------------------------------------------------
Five of these URLs answered HTTP 200 for an unknown number of weeks while
serving no county at all, and nothing in the repo could have noticed: the link
gate reads STATUS CODES, and every one of these was a clean 200. They were
found only because a reader reported that Dodge County's website had moved,
and the report generalised — the other four came out of sweeping the whole
table for the same shape.

  Dodge         co.dodge.wi.us          261 bytes: "This site has permanently
                                        moved. Please redirect your browser to
                                        http://co.dodge.wi.gov"
  Kewaunee      kewauneeco.com          114 bytes of JavaScript redirecting to
                                        a domain-parking /lander. The county is
                                        on kewauneeco.ORG.
  Rusk          ruskcountywi.gov        the same parking lander. The county is
                                        on ruskcounty.org.
  Fond Du Lac   fdlco.wi.gov (bare,     the stock "IIS Windows Server" splash.
                over http)              The county is on www.fdlco.wi.gov,
                                        which 403s this client and serves
                                        browsers.
  Pierce        co.pierce.wi.us (bare)  a noindex staff page titled "Pierce
                                        County Internal", whose own first link
                                        is "Back to Main" -> www.co.pierce.wi.us.

Two of those are worse than a dead link rather than better: a parking lander is
a page this project sent a reader to under the caption of their own county
board. THE FAILURE IS SHARED BETWEEN THE STALE TABLE AND THE GATE THAT CANNOT
SEE IT, so `--probe` reads the BODY — under 4 KB, or carrying one of the four
measured stub markers, is a finding. It is an operator step and not CI: it
needs the network, and 72 counties' hosts have their own bad days.

EVERY REPLACEMENT HAS A SECOND WITNESS. data/app/wi-county-clerks.json is built
from the Wisconsin County Clerks Association, an entirely separate publisher,
and its `website` for all five is the host chosen here (its Rusk entry is
ruskcounty.org while its own Rusk clerk e-mail is still @ruskcountywi.us, which
is the same split Dodge has: THE MAIL DOMAIN AND THE WEB DOMAIN MOVE
SEPARATELY, so a dead website is never evidence about an address). Dodge's own
county clerk page still prints dvanegtern@co.dodge.wi.us, on the .gov site, so
that address is current and is left alone.
name and 404s. Every URL below was fetched AND READ (re-measured 2026-08-29):
59 answer 200 with the county's own page, 12 answer 403 to a datacenter client
while serving browsers normally, and Taylor sits behind an sgcaptcha challenge
that a person passes and no automation here tries to.

THAT SWEEP READ STATUS CODES AND NEVER READ WHAT ANSWERED (corrected
2026-08-29)
-----------------------------------------------------------------------
It was provoked by one report — the operator noticing that Fond du Lac's
`http://fdlco.wi.gov/` needed https — and six of the seventy-two were wrong,
every one of them a link that PASSED the sweep that built this table:

  * Fond du Lac's `http://fdlco.wi.gov/` answered 200 with 703 bytes of the
    stock "IIS Windows Server" placeholder. The county is on
    `https://www.fdlco.wi.gov/`, which this repo already carried in
    wi-county-clerks.json and wi-circuit-judges.json — so the one table that
    sent readers anywhere had the only copy of the wrong host.
  * Kewaunee's `kewauneeco.com` and Rusk's `ruskcountywi.gov` answered 200
    with a 114-byte script that sends a browser to `/lander` — a GoDaddy
    PARKING page (`_trfd.push({ap:"parking"})`, img1.wsimg.com/parking-lander).
  * Dodge's `co.dodge.wi.us` answered 200 with 261 bytes reading "This site
    has permanently moved. Please redirect your browser to co.dodge.wi.gov" —
    a sentence, not a redirect: nothing forwards a reader.
  * Barron and Shawano were recorded above as answering 503. They reset the
    connection, and neither is the county: barroncountywi.gov and
    co.shawano.wi.us both serve their board pages to this client. A HOST IS
    NOT A COUNTY (Illinois learned the same thing at Knox).

    BARRON, 2026-09-02: THAT FIX WAS RIGHT AND IT STOPPED AT THE FRONT DOOR.
    Finding the host that serves a county's board page is not the same as
    reading it, and this line went in without anyone asking whether the page
    NAMES ANYONE. It does not — 75 KB of prose and two people — so Barron
    stayed in the "publishes no district-keyed member list" gap for a week
    while its own board page linked the roster twice, as "Individual Contact
    Information for County Board Supervisors". That table lives on the
    county's OTHER site, www.co.barron.wi.us/board.cfm: all 29 districts with
    their wards, supervisor, phone and county mailbox, now the scraper's
    source. Two further corrections came with it. The bare host and the www
    host are DIFFERENT ADDRESSES (173.248.55.40 and .39) and only the bare one
    fails, so "co.barron.wi.us resets" was true of a host and read as true of
    a site. And WHY it fails is not something this project can state from
    here: the sandbox's egress gateway re-signs every certificate, so a chain
    read from this vantage is the proxy's, and a reset seen here may be too.

Only ONE of the six was reachable-but-wrong in a way a status check could
ever have seen. The other five are the hollow-page class scripts/
validate_card_links.py already measures for the Illinois cards and that this
table was built without: A 200 IS NOT A PAGE. Anything added here is fetched
AND READ.

The three parked/dead hosts were also findable with no network at all, which
is why `_cross_check_scraper_hosts` below is now a gate: wi_county_board_
scraper.py reads Kewaunee's, Rusk's and Shawano's supervisors WEEKLY, from
kewauneeco.org, ruskcounty.org and co.shawano.wi.us. Two tables in this repo
named different hosts for the same county's board, the working one was right
all three times, and nothing compared them.

`seats` is the county's district count as SHIPPED — read back from the built
geometry rather than restated here, so the two can never disagree. The
counties marked below are the ones whose own board page independently named
districts 1..n matching that count when swept. Fond du Lac's mark is the one
read from an Internet Archive snapshot (2026-05-11) rather than live: its
Akamai edge refuses this client, and the page is paginated — "1 - 20 of 25
items" over districts 1..25, the count the shipped geometry carries.

Usage:
    python3 wi/scripts/build_wi_county_board_directory.py
    python3 wi/scripts/build_wi_county_board_directory.py --check
    python3 wi/scripts/build_wi_county_board_directory.py --probe   # operator, needs network
"""

import json
import os
import re
import ssl
import sys
import urllib.error
import urllib.request
import urllib.parse

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_DATA_DIR = os.path.join(REPO_ROOT, "data", "app")
GEOMETRY = os.path.join(APP_DATA_DIR, "county-supervisory-districts.json")
OUT = os.path.join(APP_DATA_DIR, "county-board-directory.json")
EXPECT_COUNTIES = 72

# county FIPS -> (name as LTSB spells it, the county's own official page).
# Hand-verified; see the module docstring for why this is not derived.
COUNTY_SITES = {
    "55001": ("Adams", "https://www.co.adams.wi.us/"),
    "55003": ("Ashland", "https://ashlandcountywi.gov/bos"),  # its board page, one paragraph per district with the supervisor and composition
    "55005": ("Barron", "https://www.barroncountywi.gov/index.asp?SEC=%7bB7F5AB49-3697-4A2E-8327-26847A43F33E%7d&Type=B_BASIC"),  # the county's canonical County Board page. It names two people and LINKS the table that names all 29, on the county's other site — see the docstring; wi_county_board_scraper.py reads that one
    "55007": ("Bayfield", "https://bayfieldcounty.wi.gov/295/Board-of-Supervisors"),  # county page confirms 1..13
    "55009": ("Brown", "https://www.browncountywi.gov/government/county-board-of-supervisors/"),  # county page confirms 1..26
    "55011": ("Buffalo", "https://www.buffalocountywi.gov/"),
    "55013": ("Burnett", "https://burnettcountywi.gov/264/Supervisors"),  # county page confirms 1..21
    "55015": ("Calumet", "https://calumetcounty.org/"),
    "55017": ("Chippewa", "https://chippewacountywi.gov/162/County-Board-Supervisors"),  # county page confirms 1..21
    "55019": ("Clark", "https://www.clarkcountywi.gov/"),
    "55021": ("Columbia", "https://www.co.columbia.wi.us/ColumbiaCounty/"),
    "55023": ("Crawford", "https://www.crawfordcountywi.gov/"),
    "55025": ("Dane", "https://board.danecounty.gov/Supervisors"),
    "55027": ("Dodge", "https://www.co.dodge.wi.gov/government/county-board/members"),  # county page confirms 1..33
    "55029": ("Door", "https://co.door.wi.gov/"),
    "55031": ("Douglas", "https://douglascountywi.gov/647/Members-by-District"),  # its Members by District table, keyed by ORDINAL words
    "55033": ("Dunn", "https://dunncountywi.gov/supervisors"),  # county page confirms 1..29
    "55035": ("Eau Claire", "https://eauclairecounty.gov/board_of_supervisors/district_representatives.php"),  # county page confirms 1..29
    "55037": ("Florence", "https://www.florencecountywi.com/government/boards_and_committees/"),  # its board list, which names all 12 with their districts; the county home page this table had names nobody
    "55039": ("Fond Du Lac", "https://www.fdlco.wi.gov/government/county-board-supervisors"),  # county page confirms 1..25
    # http://fdlco.wi.gov/ answers 200 with a default "IIS Windows Server"
    # placeholder — 703 bytes, no county content — so the card footer linked
    # a blank page for as long as this row has existed. A 200 is not a page.
    # Measured 2026-08-29 while re-probing the counties this instance had
    # recorded as refusing browser headers.
    "55039": ("Fond Du Lac", "https://www.fdlco.wi.gov/"),
    "55041": ("Forest", "https://co.forest.wi.gov/county-board-supervisors"),  # its board page, which names all 21; the county HOME page this table had names nobody. Note the bare host answers and www. does not — the opposite of Barron
    "55043": ("Grant", "https://co.grant.wi.gov/"),  # county page confirms 1..17
    "55045": ("Green", "https://greencountywi.org/164/County-Board-of-Supervisors"),  # county page confirms 1..31
    "55047": ("Green Lake", "https://www.greenlakecountywi.gov/"),
    "55049": ("Iowa", "https://www.iowacountywi.gov/"),
    "55051": ("Iron", "https://www.co.iron.wi.gov/190/County-Board"),  # its board page, which links each member's own page — where the district is
    "55053": ("Jackson", "https://www.co.jackson.wi.us/"),
    "55055": ("Jefferson", "https://jeffersoncountywi.gov/county_government/county_board/county_board_information/index.php"),  # county page confirms 1..30
    "55057": ("Juneau", "https://www.co.juneau.wi.gov/"),
    "55059": ("Kenosha", "https://www.kenoshacountywi.gov/142/County-Board-Supervisor-Districts"),  # county page confirms 1..23
    "55061": ("Kewaunee", "https://www.kewauneeco.org/government/boards_and_committees/"),  # county page confirms 1..20
    "55063": ("La Crosse", "https://lacrossecounty.org/"),
    "55065": ("Lafayette", "https://lafayettecountywi.org/"),
    "55067": ("Langlade", "https://www.co.langlade.wi.us/government/board_and_committees/"),  # county page confirms 1..21
    # THE CARD'S FOOTER LINK IS FOR A READER'S BROWSER, NOT FOR THIS CLIENT.
    # Lincoln's site sits behind a Cloudflare managed challenge that refuses
    # every automated client here and that a person's browser clears without
    # noticing, so this URL is unreachable to the probe above and correct on
    # the card. The county's board page (bc-county-board) is what its own GIS
    # layer links from every district, and it is where a reader checking a
    # name should land.
    "55069": ("Lincoln", "https://www.co.lincoln.wi.us/bc-county-board"),
    "55071": ("Manitowoc", "https://manitowoccountywi.gov/"),
    "55073": ("Marathon", "https://marathoncounty.gov/"),
    "55075": ("Marinette", "https://www.marinettecountywi.gov/county_board/"),
    "55077": ("Marquette", "https://www.marquettecountywi.gov/government/county-board-supervisors/"),  # county page confirms 1..17
    # `seats` here is the DISTRICT count read back from the shipped geometry,
    # and Menominee is the one county where that is not the size of its board:
    # the joint County/Town board seats seven, five by ward and two elected
    # countywide. The card states both, from the roster's own at-large row.
    "55078": ("Menominee", "https://www.co.menominee.wi.us/county-board/"),  # county page confirms 1..5
    "55079": ("Milwaukee", "https://county.milwaukee.gov/EN"),
    "55081": ("Monroe", "https://co.monroe.wi.us/"),
    # /307 is the MAP INDEX — 31 links to 31 PDFs with nobody's name on them —
    # and this table pointed at it while /453/County-Board named all 31 members
    # the whole time. The card links the page that names your supervisor.
    "55083": ("Oconto", "https://www.ocontocountywi.gov/453/County-Board"),  # county page confirms 1..31
    "55085": ("Oneida", "https://www.oneidacountywi.gov/"),
    "55087": ("Outagamie", "https://www.outagamie.gov/"),
    # The BOARD page, not the /2206/Supervisory-District-Maps page this row
    # used to hold: the maps page is what made Ozaukee look map-only for four
    # days (wi_county_board_scraper.py). It names all 26 districts AND their
    # supervisors, so it confirms the count and is where the roster is read.
    "55089": ("Ozaukee", "https://ozaukeecounty.gov/701/County-Board"),  # county page confirms 1..26
    "55091": ("Pepin", "https://www.co.pepin.wi.us/"),
    "55093": ("Pierce", "https://www.co.pierce.wi.us/"),
    "55095": ("Polk", "https://www.polkcountywi.gov/government/county_board_of_supervisors/index.php"),  # county page confirms 1..15
    "55097": ("Portage", "https://www.co.portage.wi.gov/"),  # county page confirms 1..25
    "55099": ("Price", "https://co.price.wi.us/"),
    "55101": ("Racine", "https://racinecounty.gov/"),
    "55103": ("Richland", "https://richlandcountywi.gov/"),
    "55105": ("Rock", "https://co.rock.wi.us/"),
    "55107": ("Rusk", "https://ruskcounty.org/supervisors"),  # county page confirms 1..19
    # WAS THE COUNTY'S HOME PAGE, which links NOTHING about the board — zero
    # anchors on sccwi.gov/ match board, supervisor or district, so a reader
    # sent there could not reach their own board and neither could this repo's
    # own sweeps, which is why the county sat in the gap block until
    # 2026-09-02 with its whole 19-seat roster published two clicks in.
    "55109": ("St Croix", "https://sccwi.gov/477/County-Board-of-Supervisors"),  # county page confirms 1..19
    "55111": ("Sauk", "https://www.co.sauk.wi.us/countyboard/sauk-county-board-members"),
    "55113": ("Sawyer", "https://www.sawyercounty.gov/directory.aspx?did=33"),  # its Board of Supervisors staff directory; redirects to the /m/ responsive template
    "55115": ("Shawano", "https://www.co.shawano.wi.us/county_board/"),  # county page confirms 1..27
    "55117": ("Sheboygan", "https://sheboygancounty.com/"),
    "55119": ("Taylor", "https://co.taylor.wi.us/"),
    "55121": ("Trempealeau", "https://co.trempealeau.wi.us/"),  # county page confirms 1..17
    "55123": ("Vernon", "https://www.vernoncountywi.gov/government/county_board_of_supervisors/index.php"),  # county page confirms 1..19
    "55125": ("Vilas", "http://www.vilascountywi.gov/departments/administration___officials/county_board_members/index.php"),  # county page confirms 1..21
    "55127": ("Walworth", "https://co.walworth.wi.us/534/Board-of-Supervisors"),  # county page confirms 1..11
    "55129": ("Washburn", "https://co.washburn.wi.us/county-board-supervisors/"),  # county page confirms 1..21
    "55131": ("Washington", "https://www.washcowisco.gov/departments/county_board"),  # county page confirms 1..21
    "55133": ("Waukesha", "https://www.waukeshacounty.gov/waukesha-county-board/"),  # county page confirms 1..25
    "55135": ("Waupaca", "https://www.waupacacounty-wi.gov/"),
    "55137": ("Waushara", "https://www.wausharacountywi.gov/13370/county-board-of-supervisors"),  # county page confirms 1..11
    "55139": ("Winnebago", "https://www.winnebagocountywi.gov/703/County-Board-of-Supervisors"),  # county page confirms 1..36
    "55141": ("Wood", "https://woodcountywi.gov/CountyBoard/"),  # county page confirms 1..19
}


# --- the --probe reader -------------------------------------------------------
# WHY A STATUS CODE IS NOT AN ANSWER HERE. Five of these URLs answered HTTP 200
# for weeks while serving no county at all (see the docstring), so this reads
# the BODY. The markers below are the four shapes that were actually measured;
# it reports rather than repairs, because which page replaces a dead one is a
# judgement (a county home page, or the board page that confirms 1..n) and is
# made by hand above.
# THE PROBE ASKS WITH THE SCRAPER'S OWN HEADERS, NOT A SECOND WEAKER COPY.
# This file used to carry its own PROBE_UA — a Chrome User-Agent plus an Accept
# and nothing else — while wi_county_board_scraper.py asked the same 72 hosts
# with a fuller set and a per-host exception table (`headers_for`). The probe
# was therefore a worse client than the scraper it exists to check, and it
# reported counties blocked that the weekly run reads perfectly well.
#
# MEASURED 2026-09-02 over all 72 county sites, same process, same minute,
# urllib both times:
#
#     PROBE_UA (this file's old set)     13 of 72 answered non-200
#     headers_for() (the scraper's)       6 of 72 answered non-200
#
# The seven that recovered are Fond du Lac, Marathon, Monroe, Outagamie,
# Racine, Rock and Sheboygan, returning 21 KB to 200 KB of real county
# navigation where the old set got a 403.
#
# WHAT `headers_for` CHOOSES BETWEEN CHANGED ON 2026-09-12 and the rule here
# did not: it is still the scraper's own answer, asked rather than guessed.
# The scraper now sends the districtry token to every host but the six
# measured refusing it, so this probe does too — which is the point of asking,
# since a copy of the old three-way table would now be probing 70 of its 72
# hosts as a client the weekly run no longer uses.
#
# OUTAGAMIE IS WHY THIS MATTERS RATHER THAN BEING A TIDY-UP. A 403 is excused
# below as "the county's host declining THIS client", so the probe SKIPS it —
# which means the one county whose fetch this repo had already solved was the
# one county the probe would never actually check. Had its URL gone stale the
# probe would have said "blocked" forever and never noticed.
#
# WHICH SINGLE HEADER DOES IT IS NOT CLAIMED, because the isolation runs that
# would answer it were confounded: attempts to bisect the header set with
# `requests` returned 403 for every variant including the full one, on hosts
# that answer 200 to urllib with those same headers. The client's own
# fingerprint is doing some of the work, so only the paired measurement above
# is asserted. What is settled is the rule: ONE source of truth for how this
# fleet asks a Wisconsin county for a page, and it lives in the scraper.
PROBE_UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
}


def probe_headers(fips, url):
    """The scraper's own per-host header set, with this file's as the fallback.

    Imported per call rather than at module scope for the reason
    `_cross_check_scraper_hosts` does it: this builder must stay runnable when
    the scraper is not importable. A fallback is announced rather than silent —
    a probe quietly running as the weaker client is exactly the failure this
    function was written to end.
    """
    try:
        from wi_county_board_scraper import headers_for
    except Exception as exc:  # pragma: no cover - import-environment only
        print("probe: wi_county_board_scraper not importable (%s); asking with "
              "this file's weaker PROBE_UA, which reports ~7 more counties "
              "blocked than the weekly run actually sees" % type(exc).__name__,
              file=sys.stderr)
        return PROBE_UA
    return headers_for(url)
# A real county site is tens of KB of navigation. Every stub measured was under
# 4 KB and every live county over 20 KB, so the floor sits between them and is
# reported, never enforced.
PROBE_MIN_BYTES = 4000
PROBE_STUBS = re.compile(
    r"(?i)permanently moved|redirect your browser|/lander|iis windows server|"
    r"page not found|domain (?:is )?for sale")


def probe():
    """Fetch every URL and say which are no longer the county's own site."""
    findings = []
    for fips, (name, url) in sorted(COUNTY_SITES.items(), key=lambda kv: kv[1][0]):
        try:
            req = urllib.request.Request(url, headers=probe_headers(fips, url))
            with urllib.request.urlopen(req, timeout=35,
                                        context=ssl.create_default_context()) as r:
                body = r.read(200000)
                code = r.status
        except urllib.error.HTTPError as e:
            # A refusal is the county's host declining THIS client; it is not a
            # stale URL and is not a finding. The docstring records the bucket.
            # 429 is rate limiting, and a serial sweep of 72 hosts can cause
            # it — back off and re-run that county rather than reading it as
            # a block.
            print("%-12s %-18s blocked (HTTP %s)%s"
                  % (name, fips, e.code, " — rate limited, re-run" if e.code == 429 else ""),
                  file=sys.stderr)
            continue
        except Exception as e:  # DNS, reset, timeout — same reasoning
            print("%-12s %-18s unreachable (%s)" % (name, fips, type(e).__name__), file=sys.stderr)
            continue
        if code == 202:
            # "Accepted" is never a document — it is what Taylor's sgcaptcha
            # returns in front of a live page. An access control, not a stale
            # URL (the same inversion validate_sources.py applies).
            print("%-12s %-18s blocked (HTTP 202, challenge)" % (name, fips), file=sys.stderr)
            continue
        text = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", body.decode("utf-8", "replace"))
        text = re.sub(r"\s+", " ", re.sub(r"(?s)<[^>]+>", " ", text)).strip()
        stub = PROBE_STUBS.search(text) or PROBE_STUBS.search(body.decode("utf-8", "replace"))
        if code == 200 and len(body) >= PROBE_MIN_BYTES and not stub:
            print("%-12s %-18s ok (%d bytes)" % (name, fips, len(body)), file=sys.stderr)
            continue
        why = "matched %r" % stub.group(0) if stub else "%d bytes" % len(body)
        findings.append((name, fips, url, why, text[:90]))
        print("%-12s %-18s SUSPECT — HTTP %s, %s" % (name, fips, code, why), file=sys.stderr)
    if findings:
        print("\n%d URL(s) answer but are not the county's site:" % len(findings), file=sys.stderr)
        for name, fips, url, why, text in findings:
            print("  %s (%s) %s\n    %s | %s" % (name, fips, url, why, text), file=sys.stderr)
        return 1
    print("\nall %d URLs serve a county site" % len(COUNTY_SITES), file=sys.stderr)
    return 0
def _cross_check_scraper_hosts():
    """Where BOTH tables name a county's board page, they must name one host.

    THE GATE THAT WOULD HAVE CAUGHT THREE OF THE SIX, offline and in a
    millisecond. wi_county_board_scraper.py fetches Kewaunee's, Rusk's and
    Shawano's supervisors every week and had their working hosts all along
    (kewauneeco.org, ruskcounty.org, co.shawano.wi.us) while this table sent
    readers to two GoDaddy parking landers and a host that resets. Two tables
    in one repo named different hosts for the same county's board, the
    scraped one was right three times out of three, and nothing compared them.

    A leading `www.` is ignored on both sides — that is a CMS's habit, not a
    disagreement. Only wi_county_board_scraper.COUNTIES is compared: its
    ARCGIS_COUNTIES are feature services (arcgis.com is nobody's board page)
    and DOCUMENT_ROSTERS is Taylor, whose host answers a captcha to everything.
    A future county that genuinely needs two hosts fails here and gets a line
    saying why, which is the point. SAUK IS THE FIRST, and it is a real two-host
    county rather than a stale entry: co.sauk.wi.us/countyboard/... is the board
    page a reader is sent to, and it links its own membership as a "Committee
    Database" served by the county's Domino application on
    saukdomino.co.sauk.wi.us — the FIELDED table the scraper reads. Both hosts
    are the county's, both answer 200, and each is right for its own job, so the
    exception is named here with its reason rather than either URL being bent to
    match the other.
    """
    TWO_HOST_COUNTIES = {
        "55111": "the board page and the county's own Domino membership database",
        # Waupaca's board page names NOBODY — four paragraphs about what a
        # county board is, and zero "District n" — while its Clerk's Directory
        # of Public Officials names all 27 district-keyed on the county's other
        # host (public4.co.waupaca.wi.us, the same domain the supervisors'
        # mailboxes sit on). Both hosts are live and both are the county's: this
        # is a county with two publishers, not the dead-domain case the error
        # below describes, so the card keeps linking the county's own site while
        # the roster is read from the Clerk's.
        "55135": "the county's own site and the Clerk's directory of officials",
        # Barron is the third, and it is the reason this gate now reads the
        # single-county carriers too. barroncountywi.gov is the county's
        # canonical County Board page and names two people; the table naming
        # all 29 is on the county's OTHER site, www.co.barron.wi.us/board.cfm,
        # which that page links twice. Both are the county's, both answer, and
        # each is right for its own job — the card sends a reader to the board
        # page, the scraper reads the roster.
        "55005": "the county's board page and the roster table it links on the "
                 "county's other site",
    }
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    try:
        from wi_county_board_scraper import COUNTIES as SCRAPED
        from wi_county_board_scraper import SINGLE_COUNTY_CARRIERS
    except ImportError as e:  # pragma: no cover - the scraper is stdlib-only
        raise RuntimeError("cannot import wi_county_board_scraper to cross-check "
                           "hosts (%s)" % e)

    # THE CARRIERS THIS GATE COULD NOT SEE. It compared COUNTIES alone, so the
    # eight counties read by a carrier of their own — Clark, Pierce, Marathon,
    # St. Croix, Chippewa, Menominee, Langlade, Barron — were outside it
    # entirely, and a directory link that went stale for any of them would have
    # gone on pointing readers at a dead page with this gate reporting a count
    # and no disagreement. Barron is how that surfaced: it is a real two-host
    # county, and the gate whose whole job is to notice two hosts never saw it.
    # A gate's own coverage is a claim, and this one was never measured.
    SCRAPED = list(SCRAPED) + [
        (spec["fips"], spec["name"], spec.get("seats"), None, spec["source_url"])
        for spec, _strategy in SINGLE_COUNTY_CARRIERS]

    def host(url):
        h = urllib.parse.urlparse(url).netloc.lower()
        return h[4:] if h.startswith("www.") else h

    disagree = []
    for fips, _name, _seats, _direction, scraped_url in SCRAPED:
        if fips not in COUNTY_SITES or fips in TWO_HOST_COUNTIES:
            continue
        ours = COUNTY_SITES[fips][1]
        if host(ours) != host(scraped_url):
            disagree.append("  %s %s\n    directory: %s\n    scraper:   %s"
                            % (fips, COUNTY_SITES[fips][0], ours, scraped_url))
    if disagree:
        raise RuntimeError(
            "%d county/counties name different board hosts in this table and in "
            "wi_county_board_scraper.COUNTIES. The scraper's host is the one "
            "proven weekly, so check THIS table first — every case measured so "
            "far was a dead or parked domain here:\n%s"
            % (len(disagree), "\n".join(disagree)))
    print("cross-check: %d counties in both tables agree on the board's host"
          % sum(1 for r in SCRAPED if r[0] in COUNTY_SITES), file=sys.stderr)


def main():
    if "--probe" in sys.argv[1:]:
        return probe()
    check_only = "--check" in sys.argv[1:]
    with open(GEOMETRY) as f:
        geo = json.load(f)

    seats = {}
    names = {}
    for feat in geo["features"]:
        p = feat["properties"]
        seats[p["CNTY_FIPS"]] = max(seats.get(p["CNTY_FIPS"], 0), int(p["SUPERID"]))
        names[p["CNTY_FIPS"]] = p["CNTY_NAME"]

    if len(seats) != EXPECT_COUNTIES:
        raise RuntimeError("geometry covers %d counties, expected %d" % (len(seats), EXPECT_COUNTIES))
    missing = sorted(set(seats) - set(COUNTY_SITES))
    extra = sorted(set(COUNTY_SITES) - set(seats))
    if missing or extra:
        raise RuntimeError("county table and geometry disagree — missing %s, extra %s"
                           % (missing, extra))
    for fips, (name, url) in COUNTY_SITES.items():
        if name != names[fips]:
            raise RuntimeError("county %s is %r in the geometry and %r in the table"
                               % (fips, names[fips], name))
        if not url.startswith("https://") and not url.startswith("http://"):
            raise RuntimeError("county %s has no usable URL: %r" % (fips, url))

    _cross_check_scraper_hosts()

    directory = {
        fips: {"county": name, "seats": seats[fips], "url": url}
        for fips, (name, url) in sorted(COUNTY_SITES.items())
    }
    total = sum(v["seats"] for v in directory.values())
    print("county-board-directory: %d counties, %d supervisory seats, %d official links"
          % (len(directory), total, len(directory)), file=sys.stderr)

    payload = json.dumps(directory, indent=1, sort_keys=True) + "\n"
    if check_only:
        # The DRIFT gate, and it has to compare bytes rather than re-run the
        # validation above: `seats` is read back from the geometry, so the way
        # these two files come apart is someone rebuilding the districts and
        # not rebuilding this — which every check above still passes.
        try:
            with open(OUT) as f:
                shipped = f.read()
        except OSError as e:
            raise RuntimeError("data/app/county-board-directory.json is missing (%s) — run this "
                               "script without --check" % e)
        if shipped != payload:
            raise RuntimeError(
                "data/app/county-board-directory.json has drifted from the shipped districts. "
                "Re-run: python3 wi/scripts/build_wi_county_board_directory.py"
            )
        print("check: shipped directory matches the shipped districts", file=sys.stderr)
        return

    with open(OUT, "w") as f:
        f.write(payload)
    print("wrote data/app/county-board-directory.json", file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main() or 0)
