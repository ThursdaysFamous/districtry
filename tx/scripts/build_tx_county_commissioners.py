#!/usr/bin/env python3
"""Write tx/data/app/tx-county-commissioners.json: the four commissioners of a
Texas county's commissioners court, read from that county's own website, for
the counties whose pages are read here. The County card names them beside the
county judge, who comes from tx-county-officials.json.

WHY COUNTY BY COUNTY. A Texas county is governed by a commissioners court: the
county judge, elected by the whole county, and four commissioners, each
elected from one commissioner precinct (Tex. Const. art. V, sec. 18). 254
counties, so 1,016 commissioners, and measured 2026-11-16 no state office
publishes a list of them: the Office of Court Administration's judicial
directory, which names the county judges, lists courts and so not the
commissioners; the Secretary of State's election results site answers this
project's reader with a managed challenge, which is never worked around; and
the Texas Association of Counties is an association of the counties, not a
government. Adam chose on 2026-11-17 to read each county's own website,
largest county first. COUNTIES below is that list as far as it has been read.

WHAT EACH COUNTY'S PAGE IS, MEASURED 2026-11-16 AND 2026-11-17 with this
script's own client (scraper_common.UA_HEADERS_ROSTER_BOT on the requests
stack), one GET each after a read of the host's robots.txt. They are the
largest counties, by the 2020 census, whose own sites serve this client and
print the four names in a form a parser can hold: the first twelve measured
2026-11-16 and 2026-11-17, and sixteen more, the 21st to 40th largest, on
2026-11-17:

  Harris    The county's Precinct 4 office's page of the whole court, on the
            county's domain; the name above "Commissioner Precinct N".
  Dallas    Dallas calls its commissioner precincts DISTRICTS. The court page
            names the four in links to /government/comcrt/districtN/; the menu
            links the same addresses as "Commissioner District N".
  Tarrant   "Commissioner Precinct N -" and the name on the next line, printed
            in the page and again in its menu; both must agree.
  Travis    "Precinct One - <name>" to "Precinct Four - <name>".
  Collin    "Precinct N –" (an en dash) and the name on the next line, under
            "Elected Commissioners". The host publishes no robots.txt (404).
  Denton    The name above "Commissioner Precinct N".
  Fort Bend "Commissioner Pct N <name>" on one line, in the court page's menu.
  Hidalgo   "Commissioner Precinct N" and the name on the next line.
  El Paso   One page per commissioner; the name above "County Commissioner,
            Precinct 1", "Commissioner Pct 3" and the like.
  Cameron   "Commissioner Pct. N, <name>" in the menu every page carries, read
            from the home page.
  Webb      One page per commissioner; the name above "Commissioner Precinct
            N", printed with "Honorable" before it, which is dropped.
  Lubbock   One page per commissioner; "County Commissioner - Precinct N" and
            the name on the next line. Its robots.txt asks for 300 seconds
            between requests, so its four pages take about twenty minutes.
  Jefferson One page per commissioner; "Commissioner Precinct N", the line
            "JEFFERSON COUNTY", then the name.
  Ellis     One page per commissioner; the name above "Commissioner" in the
            page's contact block.
  Guadalupe "Commissioner, Pct N" and the name on the next line.
  Midland   The court's "Members of the Court" page; the name below
            "Commissioner Precinct N". It names an Acting County Judge.
  Ector     "Precinct N" and "Commissioner <name>" on the next line, on the
            county's pages at the state's CIRA host (newtools.cira.state.tx.us),
            which publishes no robots.txt (404).
  Comal     The name above "Commissioner, Precinct N".
  Parker    "Commissioner Precinct N" and "Commissioner <name>" on the next
            line; the menu prints the label again with no name, and is passed.
  Kaufman   "Precinct N Commissioner <name>" on one line, in the page's list
            of the court's members.
  Taylor    One page per commissioner; the name above "Commissioner Precinct N"
            in the page's contact block (the page's own text calls some of them
            by surname alone, and is not read).
  Randall   The name above ", Precinct N".
  Grayson   One page per commissioner; "Grayson County Commissioner Precinct N"
            and the name on the next line. No robots.txt (404).
  Wichita   "Precinct N", "Commissioner:", then the name.
  Gregg     One page per commissioner; "<name>, Commissioner" on one line.
  Tom Green "Precinct N Commissioner" and the name on the next line with a
            party letter after it ("(R)"), which is dropped. No robots.txt.
  Potter    "Commissioner, Precinct One:" to "Four:" and the name on the next
            line, at the state's CIRA host.
  Rockwall  The name above "Precinct N Commissioner", in the home page's list
            of the court.

And nineteen of the 41st to 60th largest, measured 2026-11-17 the same way:

  Hunt      "Commissioner Precinct N: <name>" on one line. No robots.txt.
  Bastrop   One page per commissioner; the name above "Commissioner Precinct
            N". No robots.txt.
  Bowie     "Precinct N" heads each commissioner's block, and the name sits
            above "Commissioner" alone further down it, so that label takes
            the precinct of the nearest "Precinct N" above it (`heading`).
  Liberty   "Commissioner Precinct N" and the name on the next line. No
            robots.txt.
  Victoria  The name above "Commissioner - Precinct N (<place>)" or
            "Commissioner, Precinct N (<place>)", in the court page's list of
            members.
  Angelina  "Precinct N: Commissioner <name>" on one line.
  Orange    "Commissioner of Precinct N, <name>; <telephone>" on one line; the
            telephone is not kept.
  Coryell   "Precinct N: <name>" on one line. No robots.txt.
  Henderson One page per commissioner; the name below "Contact Us", printed
            there as "Charles Chuck McHam" where the court page has "Charles
            (Chuck) McHam", which the name test did not take when this county
            was added. It takes a nickname in brackets since the 61st to 80th
            were added (Chambers, below); Henderson is still read from the
            commissioners' own pages, so its record did not change.
  Walker    One page per commissioner, each precinct's road and bridge page;
            the name, a comma on a line of its own, then "Commissioner
            Precinct N". Its robots.txt asks for 300 seconds between
            requests, Lubbock's figure, so its four pages take about fifteen
            minutes and the weekly job's time limit is an hour.
  Harrison  "Precinct N" and the name on the next line. No robots.txt.
  San Patricio
            "Commissioner Precinct N - <name>" on one line. No robots.txt.
  Wise      "Commissioner Precinct N:" and the name on the next line.
  Starr     "Precinct N Commissioner" and the name on the next line. No
            robots.txt.
  Nacogdoches
            The name above "Precinct N Commissioner".
  Hood      One page per commissioner; the name above "Commissioner Precinct
            N". No robots.txt.
  Van Zandt "Precinct N Commissioner" and the name on the next line, at the
            state's CIRA host. No robots.txt.
  Anderson  "County Commissioner Precinct N" and the name on the next line.
            No robots.txt.
  Waller    One page per commissioner; "Precinct N Commissioner - <name>" on
            one line. No robots.txt.

And nineteen of the 61st to 80th largest, measured 2026-11-17 the same way:

  Hardin    "Pct. N <name>" on one line, under "county commissioners Contact
            Information". No robots.txt.
  Navarro   "Precinct N Commissioner" and the name on the next line. No
            robots.txt.
  Kerr      The name above "Kerr County Commissioner, Precinct N". The
            county's old host, www.co.kerr.tx.us, does not answer; the court
            page is at kerrcountytx.gov.
  Rusk      "Precinct N Commissioner" and the name on the next line. No
            robots.txt.
  Medina    "Precinct N Commissioner" (and "Commissioner Precinct 4" for the
            fourth) with the name on the next line. No robots.txt.
  Cherokee  "Precinct N Commissioner" and the name on the next line. No
            robots.txt.
  Polk      The name above ", Precinct N, County Commissioner". The county's
            old host, www.co.polk.tx.us, presents a certificate for another
            name; the county's site is polktx.gov, whose robots.txt asks for 10
            seconds between requests.
  Lamar     The name above "Precinct N Commissioner". No robots.txt.
  Wilson    "Precinct N Commissioner", a line holding only "▲" (an accordion's
            arrow), then the name. No robots.txt.
  Burnet    One page per commissioner; the name above "Precinct N
            Commissioner". Its robots.txt asks for 10 seconds between requests.
  Atascosa  The name above "County Commissioner – Precinct N", with
            "(Unexpired Term)" after it for one seat.
  Val Verde "Commissioner N" and the name on the next line, on the county's
            home page. Its robots.txt asks for 10 seconds between requests.
  Chambers  The name above "Commissioner Precinct N"; one is printed "William
            (Bill) Wallace Jr.", which is why the name test takes a nickname in
            brackets. Its robots.txt asks for 10 seconds between requests.
  Caldwell  "Precinct N Commissioner" and the name on the next line, the
            precincts printed in the order 1, 3, 2, 4. No robots.txt.
  Wood      "Precinct N Commissioner", a line holding only "▲", then the
            name. No robots.txt.
  Kendall   The name above "Commissioner Precinct N", in the staff directory's
            list of the county commissioners. Its robots.txt asks for 10
            seconds between requests.
  Cooke     "Precinct N Commissioner" and the name on the next line. No
            robots.txt.
  Wharton   "Commissioner <name>, Pct N" on one line, the period after "Pct"
            printed for one seat and not the others. No robots.txt.
  Upshur    "Commissioner Pct N" and the name on the next line, in the court
            page's table of county officers. No robots.txt.

And eighteen of the 81st to 100th largest, measured 2026-11-17 the same way:

  Jim Wells One page per commissioner; "Commissioner - Precinct N" and the
            name on the next line. No robots.txt.
  Brown     "Precinct N Commissioner" and the name on the next line. The
            county's www.browncountytx.org forwards to browncountytx.gov. No
            robots.txt.
  Hopkins   The court page's menu names the four in links to
            /page/hopkins.CommN, and each of those pages names its precinct
            (measured). No robots.txt.
  Matagorda "Precinct N Commissioner", a line holding only "▲", then the
            name. The county's www.co.matagorda.tx.us forwards to
            matagordatx.gov. No robots.txt.
  Hill      One page per commissioner; "Commissioner <name>, Pct N" on one
            line. The court page prints two of the four names inline and two on
            the next line, which one pattern cannot hold. No robots.txt.
  Washington
            "Precinct N", a line holding only "▲", then "Commissioner <name>".
            No robots.txt.
  Fannin    "Precinct N Commissioner" and the name on the next line. No
            robots.txt.
  Howard    The name above "Precinct N Commissioner". Its robots.txt asks for
            10 seconds between requests.
  Jasper    The name above "Precinct N Commissioner". No robots.txt.
  Titus     "Commissioner Precinct N" and the name on the next line. No
            robots.txt.
  Bee       The name above "Precinct N Commissioner". The county's old host,
            www.co.bee.tx.us, presents another county's certificate; its site
            is beecounty.texas.gov, whose robots.txt asks for 10 seconds
            between requests.
  Kleberg   "Precinct N Commissioner" and the name on the next line. No
            robots.txt.
  Austin    "Commissioner, Precinct N" and the name on the next line. No
            robots.txt.
  Grimes    "Commissioner Precinct N" and the name on the next line. The
            county's old host, www.co.grimes.tx.us, does not answer; its site
            is grimescountytexas.gov, whose robots.txt asks for 10 seconds
            between requests.
  Cass      "Precinct N Commissioner" and the name on the next line. No
            robots.txt.
  Palo Pinto
            One page per commissioner; "County Commissioner Precinct #N" and
            the name on the next line. The court page breaks two of the four
            labels across lines. No robots.txt.
  San Jacinto
            The name above "Commissioner, Precinct N", above "Precinct N
            Commissioner", or two lines above "Precinct 2" with "Commissioner,"
            between, which is what `up_to` is for. No robots.txt.
  Milam     "Precinct N" and the name on the next line. No robots.txt.

And fifty-four of the 101st to 160th largest, measured 2026-11-17 the same way.
Each has no robots.txt unless its entry says otherwise.

  Uvalde    "COMMISSIONER, PRECINCT ONE" (TWO, THREE, FOUR) and the name on the
            next line; the number words are read in capitals or in Title case.
            Its robots.txt permits the page.
  Fayette   "Precinct N Commissioner" and the name on the next line.
  Shelby    "Precinct N Commissioner", then up to three lines naming the
            county roads in that precinct ('"For all County Roads beginning',
            'with N"', "▲"), then the name; `up_to` again.
  Panola    The name above "Precinct N Commissioner". Its robots.txt asks for
            10 seconds between requests.
  Limestone "Precinct N Commissioner" and the name on the next line.
  Houston   "Precinct N Commissioner", a line holding only "▲", then the
            name. The page prints precincts 2 and 3 in the other order.
  Lampasas, Hockley, Moore, Llano, Gray
            "Precinct N Commissioner" and the name on the next line.
  Bandera   "Precinct N Commissioner" and "Honorable <name>" on the next
            line.
  Hutchinson
            The name above "Precinct N Commissioner", which three of the four
            labels spell "Commisioner". Its robots.txt permits the page.
  Colorado  "Commissioner, Precinct N" and the name on the next line.
  Lavaca    "COMMISSIONER PRECINCT N", a line holding only "▲", then the name.
  Willacy   "County Commissioner Precinct N", a line holding only "▲", then
            "Hon. <name>".
  Montague  "Precinct N Commissioner" and the name on the next line.
  DeWitt    The name above "Precinct N Commissioner".
  Tyler     "Commissioner Pct. N" and the name on the next line.
  Jones, Freestone, Deaf Smith
            "Precinct N Commissioner" and the name on the next line.
  Andrews   "Commissioner <name>" above ", Pct. N". Its robots.txt asks for 10
            seconds between requests.
  Frio      "Precinct N Commissioner", a line holding only "▲", then the name.
  Young     "YOUNG COUNTY COMMISSIONER PCT. N" and the name on the next line.
  Burleson  "Precinct N Commissioner - <name>" on one line. The county's
            www.co.burleson.tx.us forwards to burlesoncountytx.gov.
  Lee       "Precinct N Commissioner" and the name on the next line.
  Falls     "Commissioner Precinct N" and the name on the next line.
  Scurry    "Precinct N Commissioner" and the name on the next line.
  Robertson "PRECINCT N, COMMISSIONER" and the name on the next line.
  Leon      "PRECINCT I COMMISSIONER" (II, III, IV) and the name on the next
            line; Roman numerals are read for that.
  Pecos     "Precinct N Commissioner" and the name on the next line. Its
            robots.txt permits the page.
  Jackson   "PRECINCT N COMMISSIONER" and the name on the next line. Three of
            the four names are printed in capitals, and they ship as printed.
  Bosque    The name above "Commissioner Precinct N". The county's
            www.co.bosque.tx.us does not answer; its site is bosquecounty.gov,
            whose robots.txt asks for 10 seconds between requests.
  Eastland  A table: the four "Precinct N" headings on one row and the four
            names on the next, so each name is the fourth line after its
            heading. The county's www.co.eastland.tx.us does not answer; its
            pages are on the state's county host, newtools.cira.state.tx.us.
  Nolan     "Precinct N Commissioner" and the name on the next line.
  Karnes    "PRECINCT # N COMMISSIONER" and the name on the next line.
  Zapata    "Precinct N Commissioner", a line holding only "▲", then the name.
  Trinity   "<name> ~ PCT N" on one line, under "TRINITY COUNTY
            COMMISSIONERS".
  Madison   "Precinct N Commissioner" and the name on the next line.
  Lamb      The name above "Commissioner Precinct N".
  Wilbarger "Commissioner Precinct N", a line holding only "▲", then
            "Commissioner <name>".
  Camp, Dawson
            "Precinct N Commissioner" and the name on the next line.
  Newton    "Commissioner Precinct N" and the name on the next line.
  Rains     "Precinct N Commissioner" and the name on the next line.
  Morris    "Commissioner", then "Precinct N", then the name.
  Terry     The commissioners court page lists the county judge, then four
            people, each above "Precinct N"; the court is the judge and the
            four commissioners, so each is read as that precinct's
            commissioner.
  Ward, Red River
            "Precinct N Commissioner" and the name on the next line.
  Blanco    "Precinct N Commissioner" and the name on the next line. The
            county's www.co.blanco.tx.us forwards to blancocountytexas.gov.
  Live Oak, Franklin
            "Precinct N Commissioner" and the name on the next line.
  Callahan  "Precinct N Commissioner", a line holding only "▲", then the
            name. The county's www.co.callahan.tx.us answers with a TLS error;
            its pages are on newtools.cira.state.tx.us.

NOT READ, AND WHY, among the twenty largest:
  Bexar     www.bexar.org answered two of three reads with Cloudflare's managed
            challenge ("Just a moment..."). A host that challenges is
            challenge-fronted for every path, and getting in on the reads where
            the control happens to be off is working around it (CLAUDE.md). It
            waits for a deliberate re-measurement: three consecutive reads at
            least fifteen seconds apart serving the page.
  Montgomery, Bell
            www.mctx.org and www.bellcountytx.com publish `User-agent: *` /
            `Disallow: /` (the same 210 bytes on both), which binds this
            project. Not fetched.
  Williamson, McLennan, Hays
            www.wilcotx.gov, www.mclennan.gov and www.hayscountytx.gov answer
            this client with Cloudflare's "Sorry, you have been blocked" page
            (HTTP 403) on the page and on robots.txt.
  Brazoria, Galveston, Nueces
            Each answers this client with Akamai's "Access Denied" (HTTP 403)
            on the page and on robots.txt.
  The last six refuse this project's own client. CLAUDE.md allows a browser
  identity where a site measurably refuses ours by its fingerprint, with the
  measurement recorded. On 2026-11-17 each of them, and Johnson below, served
  its robots.txt and its commissioners' pages to the fleet's Chrome client
  with its client hints (scraper_common.UA_HINTS_CHROME_126, standard-library
  stack), each robots.txt permitting those pages, and none answered with a
  challenge; whether to read them that way is Adam's decision, so until he
  makes it they are recorded here and in the gap record.

NOT READ, AND WHY, among the 21st to 40th largest (measured 2026-11-17):
  Hays      Above: Cloudflare's block page.
  Brazos    www.brazoscountytx.gov answers this client with a browser check
            ("Just a moment... Checking your browser", HTTP 403, a script
            that sends a browser on to the page) on the page and on
            robots.txt. A challenge is an access control and is never worked
            around, with any client.
  Johnson   www.johnsoncountytx.org answers this client with HTTP 403 on the
            page and on robots.txt; see the paragraph above.
  Smith     www.smith-county.com serves this client, but its precinct pages
            print each commissioner's name only inside sentences ("Christina
            Drewry took office on January 2, 2025 as ..."), which a parser
            cannot read without guessing where a name ends. The county's newer
            site, smithcounty.prod.govaccess.org, fails this client's TLS
            check, so its robots.txt cannot be read, which RFC 9309 treats as
            disallowing everything.

NOT READ, AND WHY, among the 41st to 60th largest (measured 2026-11-17):
  Maverick  www.co.maverick.tx.us, where the county's site used to be,
            answers every path asked with a 19-byte page and HTTP 404, and no
            other site of the county's was found; maverickcountytx.gov and
            maverickcounty.texas.gov do not answer.

NOT READ, AND WHY, among the 61st to 80th largest (measured 2026-11-17):
  Erath     www.co.erath.tx.us answers this client with Cloudflare's
            "Attention Required!" block page (HTTP 403) on the page and on
            robots.txt, as Williamson, McLennan and Hays do. Not measured with
            a browser identity; that waits for Adam's decision on the seven.

NOT READ, AND WHY, among the 81st to 100th largest (measured 2026-11-17):
  Hale      www.halecounty.org publishes `User-agent: *` / `Disallow: /` (210
            bytes), which binds this project; no other site of the county's
            was found. Not fetched.
  Gillespie gillespiecounty.gov serves this client, but its commissioners'
            page names nobody; the four names are printed only in a PDF list
            of elected officials it links, which this builder does not read.

NOT READ, AND WHY, among the 101st to 160th largest (measured 2026-11-17):
  Aransas   www.aransascountytx.gov answers with an Imperva (Incapsula) bot
            check, which is an access control and is not worked around.
  Gaines    The commissioners court page and the county's phone directory name
            no commissioner.
  Calhoun   Each commissioner has a "Road and Bridge Precinct N" page. Those
            for precincts 2 to 4 say the person is the county commissioner;
            the one for precinct 1 names a person and does not say so, and a
            road and bridge page can name a road superintendent, so the county
            is not read until its own site says who holds precinct 1.
  Gonzales  The court page prints precinct 2's name with mismatched quotation
            marks, which this builder refuses as not shaped like a name rather
            than correcting.
  Reeves    www.reevescounty.org answers this client with Akamai's "Access
            Denied" (HTTP 403) on the page and on robots.txt, like Brazoria,
            Galveston and Nueces above.
  Comanche  The court page spells precinct 2's commissioner two ways, "Russell
            Gilette" beside the label and "Russell Gillette" in its contact
            line, and this builder does not choose between them.

A NAME IS PRINTED AS THE COUNTY PRINTS IT, honorific and all ("Dr. Elba
Garcia"), the fleet's practice; each must pass the fleet's officeholder-name
test, carry no digit and be one of four distinct names for precincts 1 to 4.
A page whose shape changes FAILS ITS PARSER rather than yielding a guess.

A COUNTY WHOSE PAGE CANNOT BE READ KEEPS ITS LAST RECORD (Adam's rule of
2026-09-19: a refusal stops the fetch and never unpublishes what was already
read). Each record's `asOf` is the date its four names were first read in
that form: a rebuild that reads the same names keeps the old date, so a week
with no change writes the same bytes and opens no pull request. A carried
record keeps its date too, so the date is never later than the last read, and
the card says the page is looked at weekly rather than claiming the date is
the last look. Because a carried county changes no byte, --unread FILE writes
the counties not read this run, one per line, and the weekly job's last step
fails on a non-empty list, so a page that stopped reading turns the run red
instead of staying quiet behind its last record.

THE PAGES ARE SNAPSHOTS. Commissioners elected on 3 November 2026 take office
on 1 January 2027, and a county's page changes when the county changes it.

Usage:
    python3 tx/scripts/build_tx_county_commissioners.py [OUT_DIR]
    python3 tx/scripts/build_tx_county_commissioners.py --check

--check reads the SHIPPED file and nothing else, offline and with the
standard library alone: every record a county the County layer draws and
COUNTIES lists, four seats numbered 1 to 4 with four distinct names that pass
the fleet's name test, its source address one COUNTIES gives, and a dated
`asOf`. It proves the file is what a build writes; it never proves a county
has not changed its page since.

--save DIR writes each fetched page into DIR, reading back any it already
holds; --offline DIR reads them back instead of fetching. --unread FILE writes
the names of the counties not read this run (see above).
"""

import datetime
import json
import os
import re
import sys
import time
from html.parser import HTMLParser
from urllib.parse import urlsplit

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(_HERE)), "scripts"))
from robots_policy import RobotsGate  # noqa: E402  (FLEET_SHARED)
from scraper_common import (  # noqa: E402  (FLEET_SHARED)
    UA_HEADERS_ROSTER_BOT, UA_ROSTER_BOT, fetch as fetch_response)
from validate_officeholder_names import why_not_a_name  # noqa: E402  (FLEET_SHARED)

PACE_SECONDS = 1.0
INSTANCE_ROOT = os.path.dirname(_HERE)
DEFAULT_OUT_DIR = os.path.join(INSTANCE_ROOT, "data", "app")
OUT_NAME = "tx-county-commissioners.json"
COUNTIES_FILE = os.path.join(DEFAULT_OUT_DIR, "state-counties.json")
ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# A precinct printed as a word, in any case ("Precinct One", "PRECINCT ONE"),
# or as a Roman numeral ("PRECINCT III", Leon).
NUMBER_WORDS = {"ONE": 1, "TWO": 2, "THREE": 3, "FOUR": 4, "I": 1, "II": 2, "III": 3, "IV": 4}
# Words that name an office or a page part, never a person: a line carrying one
# is not a commissioner's name, whatever the line beside it says.
NOT_A_PERSON_RE = re.compile(
    r"\b(?:Commissioners?|Court|County|Judge|Precinct|Pct|District|Home|Connect|Menu|"
    r"Agenda|Agendas|Office|Contact|Us|Map|Maps|Directory|Services|Statement|Mission|"
    r"Newsletters?|Information|Resources|Welcome|Staff|Projects|Events|News|Links|"
    r"Documents|Forms|Calendar|Videos?|Live|Online|Search|Email|Biography|Meetings?)\b", re.I)
# The shape of a printed name: two to six words, each a capitalised word, an
# initial, a nickname in quotation marks or in brackets ("William (Bill)
# Wallace Jr.", as Chambers prints it), or a particle, with an optional ", Jr."
# and the like. A heading such as "Mission Statement" has this shape too, which
# is why NOT_A_PERSON_RE and the precinct label beside it are what make a line
# a name.
_WORD = (r"(?:[A-ZÀ-Þ][A-Za-zÀ-ÿ'’.-]*|\"[^\"]+\"|“[^”]+”|\([A-Z][^()]*\)"
         r"|de|del|la|los|van|von|y)")
NAME_RE = re.compile(r"^%s(?:\s+%s){1,5}(?:,\s+(?:Jr|Sr)\.?|,?\s+(?:II|III|IV))?$" % (_WORD, _WORD))
# A courtesy title some counties print before a name; it is not part of it.
# "Dr." is kept as printed, the fleet's practice.
HONORIFIC_RE = re.compile(r"^(?:The\s+)?(?:Honorable|Hon\.)\s+", re.I)
# The label most county pages print beside a commissioner's name.
LABEL = r"(?:County\s+)?Commissioner,?\s+(?:Precinct|Pct\.?)\s*(?P<n>[1-4])"

# Each county: where its names are printed and in which of four patterns.
#   name_above  the name on the line above the precinct label
#   name_below  the name on the line below it
#   inline      the label and the name on one line (a `name` group)
#   links       the name as a link's text, the precinct in the link's address
# `pages` maps each precinct to a page of its own, where a county prints each
# commissioner on that commissioner's page; only that precinct is read there,
# and there a label may name no precinct ("Commissioner" alone). `offset` puts
# the name that many lines from the label, every line between matching
# `between`; `strip` is removed from the line before it is read as a name (a
# "Commissioner " in front of it, a party letter after it). `heading` is for a
# page that prints "Precinct N" above a block and "Commissioner" alone beside the
# name: such a label takes the precinct of the nearest line above it that
# matches `heading`. With `up_to`, `offset` is the farthest the name may be:
# the lines passed over must still match `between`, but there may be fewer of
# them, as where a county prints "Commissioner, Precinct 1" on one line and
# "Commissioner," and "Precinct 2" on two (San Jacinto).
COUNTIES = [
    dict(geoid="48201", county="Harris County", seat_word="Precinct",
         url="https://cp4.harriscountytx.gov/Connect/Commissioners-Court",
         mode="name_above", label=LABEL),
    dict(geoid="48113", county="Dallas County", seat_word="District",
         url="https://www.dallascounty.org/government/comcrt/", mode="links",
         href=r"/government/comcrt/district(?P<n>[1-4])/?$", skip=r"^Commissioner District"),
    dict(geoid="48439", county="Tarrant County", seat_word="Precinct",
         url="https://www.tarrantcountytx.gov/en/commissioners-court.html",
         mode="name_below", label=r"Commissioner Precinct (?P<n>[1-4]) -"),
    dict(geoid="48453", county="Travis County", seat_word="Precinct",
         url="https://www.traviscountytx.gov/commissioners-court",
         mode="inline", label=r"Precinct (?P<n>One|Two|Three|Four) - (?P<name>.+)"),
    dict(geoid="48085", county="Collin County", seat_word="Precinct",
         url="https://www.collincountytx.gov/government/commissioners-court",
         mode="name_below", label="Precinct (?P<n>[1-4]) –", after="Elected Commissioners"),
    dict(geoid="48121", county="Denton County", seat_word="Precinct",
         url="https://www.dentoncounty.gov/165/Commissioners-Court",
         mode="name_above", label=LABEL),
    dict(geoid="48157", county="Fort Bend County", seat_word="Precinct",
         url="https://www.fortbendcountytx.gov/government/departments/commissioners-court",
         mode="inline", label=r"Commissioner Pct (?P<n>[1-4]) (?P<name>.+)"),
    dict(geoid="48215", county="Hidalgo County", seat_word="Precinct",
         url="https://www.hidalgocounty.us/2179/Commissioners",
         mode="name_below", label=r"Commissioner Precinct (?P<n>[1-4])"),
    dict(geoid="48141", county="El Paso County", seat_word="Precinct",
         url="https://www.epcounty.com/165/Commissioners-Court", mode="name_above", label=LABEL,
         pages={1: "https://www.epcounty.com/194/Commissioner-Precinct-1",
                2: "https://www.epcounty.com/195/Commissioner-Precinct-2",
                3: "https://www.epcounty.com/196/Commissioner-Precinct-3",
                4: "https://www.epcounty.com/197/Commissioner-Precinct-4"}),
    dict(geoid="48061", county="Cameron County", seat_word="Precinct",
         url="https://www.cameroncountytx.gov/",
         mode="inline", label=r"Commissioner Pct\. (?P<n>[1-4]), (?P<name>.+)"),
    dict(geoid="48479", county="Webb County", seat_word="Precinct",
         url="https://www.webbcountytx.gov/170/Commissioners-Court", mode="name_above", label=LABEL,
         pages={1: "https://www.webbcountytx.gov/175/Commissioner-Pct-1",
                2: "https://www.webbcountytx.gov/176/Commissioner-Pct-2",
                3: "https://www.webbcountytx.gov/177/Commissioner-Pct-3",
                4: "https://www.webbcountytx.gov/178/Commissioner-Pct-4"}),
    dict(geoid="48303", county="Lubbock County", seat_word="Precinct",
         url="https://www.lubbockcounty.gov/department/division.php?structureid=223",
         mode="name_below", label=r"County Commissioner - Precinct (?P<n>[1-4])",
         pages={1: "https://www.lubbockcounty.gov/department/index.php?structureid=8",
                2: "https://www.lubbockcounty.gov/department/index.php?structureid=9",
                3: "https://www.lubbockcounty.gov/department/index.php?structureid=10",
                4: "https://www.lubbockcounty.gov/department/index.php?structureid=11"}),
    dict(geoid="48245", county="Jefferson County", seat_word="Precinct",
         url="https://jeffersoncountytx.gov/comm_crt/CountyJudge.htm", mode="name_below",
         label=r"Commissioner Precinct (?P<n>[1-4])", offset=2, between="JEFFERSON COUNTY",
         pages={1: "https://jeffersoncountytx.gov/CommPrt1/main.html",
                2: "https://jeffersoncountytx.gov/CommPrt2/main.html",
                3: "https://jeffersoncountytx.gov/CommPrt3/main.html",
                4: "https://jeffersoncountytx.gov/prct4/index.html"}),
    dict(geoid="48139", county="Ellis County", seat_word="Precinct",
         url="https://elliscountytx.gov/450/Commissioners", mode="name_above",
         label="Commissioner",
         pages={1: "https://elliscountytx.gov/124/Precinct-One",
                2: "https://elliscountytx.gov/125/Precinct-Two",
                3: "https://elliscountytx.gov/126/Precinct-Three",
                4: "https://elliscountytx.gov/127/Precinct-Four"}),
    dict(geoid="48187", county="Guadalupe County", seat_word="Precinct",
         url="https://www.guadalupetx.gov/page/commcourt.home", mode="name_below",
         label=r"Commissioner, Pct (?P<n>[1-4])"),
    dict(geoid="48329", county="Midland County", seat_word="Precinct",
         url="https://www.co.midland.tx.us/948/Members-of-the-Court", mode="name_below",
         label=LABEL),
    dict(geoid="48135", county="Ector County", seat_word="Precinct",
         url="https://newtools.cira.state.tx.us/page/ector.Commissioners.Court",
         mode="name_below", label=r"Precinct (?P<n>[1-4])", strip=r"^Commissioner\s+"),
    dict(geoid="48091", county="Comal County", seat_word="Precinct",
         url="https://www.comalcounty.gov/164/Commissioners-Court", mode="name_above",
         label=LABEL),
    dict(geoid="48367", county="Parker County", seat_word="Precinct",
         url="https://parkercountytx.gov/98/Commissioners-Court", mode="name_below",
         label=LABEL, strip=r"^Commissioner\s+"),
    dict(geoid="48257", county="Kaufman County", seat_word="Precinct",
         url="https://kaufmancounty.net/159/Commissioners-Court", mode="inline",
         label=r"Precinct (?P<n>[1-4]) Commissioner (?P<name>.+)"),
    dict(geoid="48441", county="Taylor County", seat_word="Precinct",
         url="https://www.taylorcounty.texas.gov/198/County-Commissioners",
         mode="name_above", label=LABEL,
         pages={1: "https://www.taylorcounty.texas.gov/199/Precinct-1",
                2: "https://www.taylorcounty.texas.gov/200/Precinct-2",
                3: "https://www.taylorcounty.texas.gov/201/Precinct-3",
                4: "https://www.taylorcounty.texas.gov/202/Precinct-4"}),
    dict(geoid="48381", county="Randall County", seat_word="Precinct",
         url="https://www.randallcounty.gov/222/Commissioners-Court", mode="name_above",
         label=r", Precinct (?P<n>[1-4])"),
    dict(geoid="48181", county="Grayson County", seat_word="Precinct",
         url="https://www.co.grayson.tx.us/page/cj.court", mode="name_below",
         label=r"Grayson County Commissioner Precinct (?P<n>[1-4])",
         pages={1: "https://www.co.grayson.tx.us/page/comp1.home",
                2: "https://www.co.grayson.tx.us/page/comp2.home",
                3: "https://www.co.grayson.tx.us/page/comp3.home",
                4: "https://www.co.grayson.tx.us/page/comp4.home"}),
    dict(geoid="48485", county="Wichita County", seat_word="Precinct",
         url="https://wichitacountytx.com/locations/commissioners-court/", mode="name_below",
         label=r"Precinct (?P<n>[1-4])", offset=2, between="Commissioner:"),
    dict(geoid="48183", county="Gregg County", seat_word="Precinct",
         url="https://greggcounty.texas.gov/government/commissioners-court", mode="inline",
         label=r"(?P<name>.+), Commissioner",
         pages={1: "https://greggcounty.texas.gov/government/precinct-1/commissioner-precinct-1",
                2: "https://greggcounty.texas.gov/government/precinct-2/commissioner-precinct-2",
                3: "https://greggcounty.texas.gov/government/precinct-3/commissioner-precinct-3",
                4: "https://greggcounty.texas.gov/government/precinct-4/commissioner-precinct-4"}),
    dict(geoid="48451", county="Tom Green County", seat_word="Precinct",
         url="https://www.tomgreencountytx.gov/page/cc.CommissionersHome", mode="name_below",
         label=r"Precinct (?P<n>[1-4]) Commissioner", strip=r"\s+\([A-Z]\)?$"),
    dict(geoid="48375", county="Potter County", seat_word="Precinct",
         url="https://newtools.cira.state.tx.us/page/potter.Commissioners.Court",
         mode="name_below", label=r"Commissioner, Precinct (?P<n>One|Two|Three|Four):"),
    dict(geoid="48397", county="Rockwall County", seat_word="Precinct",
         url="https://www.rockwallcountytexas.com/", mode="name_above",
         label=r"Precinct (?P<n>[1-4]) Commissioner"),
    dict(geoid="48231", county="Hunt County", seat_word="Precinct",
         url="https://www.huntcounty.net/page/hunt.commissionerscourt", mode="inline",
         label=r"Commissioner Precinct (?P<n>[1-4]): (?P<name>.+)"),
    dict(geoid="48021", county="Bastrop County", seat_word="Precinct",
         url="https://www.bastropcounty.gov/page/com.main", mode="name_above", label=LABEL,
         pages={1: "https://www.bastropcounty.gov/page/com.pct_1",
                2: "https://www.bastropcounty.gov/page/com.pct_2",
                3: "https://www.bastropcounty.gov/page/com.pct_3",
                4: "https://www.bastropcounty.gov/page/com.pct_4"}),
    dict(geoid="48037", county="Bowie County", seat_word="Precinct",
         url="https://www.bowiecounty.org/1194/Commissioners", mode="name_above",
         label="Commissioner", heading=r"Precinct (?P<n>[1-4])"),
    dict(geoid="48291", county="Liberty County", seat_word="Precinct",
         url="https://www.libertycountytx.gov/page/Commissioners.Court", mode="name_below",
         label=LABEL),
    dict(geoid="48469", county="Victoria County", seat_word="Precinct",
         url="https://www.victoriacountytx.gov/188/Commissioners-Court", mode="name_above",
         label=r"Commissioner(?:,| -) Precinct (?P<n>[1-4]) \(.+\)"),
    dict(geoid="48005", county="Angelina County", seat_word="Precinct",
         url="https://www.angelinacounty.net/comcourt/", mode="inline",
         label=r"Precinct (?P<n>[1-4]): Commissioner (?P<name>.+)"),
    dict(geoid="48361", county="Orange County", seat_word="Precinct",
         url="https://www.co.orange.tx.us/Commissioners", mode="inline",
         label=r"Commissioner of Precinct (?P<n>[1-4]), (?P<name>[^;]+);.*"),
    dict(geoid="48099", county="Coryell County", seat_word="Precinct",
         url="https://coryellcountytx.gov/commissioners-court/", mode="inline",
         label=r"Precinct (?P<n>[1-4]): (?P<name>.+)"),
    dict(geoid="48213", county="Henderson County", seat_word="Precinct",
         url="https://www.henderson-county.com/193/Commissioners-Court", mode="name_below",
         label="Contact Us",
         pages={1: "https://www.henderson-county.com/194/Commissioner-Precinct-1",
                2: "https://www.henderson-county.com/196/Commissioner-Precinct-2",
                3: "https://www.henderson-county.com/197/Commissioner-Precinct-3",
                4: "https://www.henderson-county.com/198/Commissioner-Precinct-4"}),
    dict(geoid="48471", county="Walker County", seat_word="Precinct",
         url="https://www.co.walker.tx.us/department/index.php?structureid=6",
         mode="name_above", label=LABEL, offset=2, between=",",
         pages={1: "https://www.co.walker.tx.us/department/index.php?structureid=30",
                2: "https://www.co.walker.tx.us/department/index.php?structureid=31",
                3: "https://www.co.walker.tx.us/department/index.php?structureid=32",
                4: "https://www.co.walker.tx.us/department/index.php?structureid=33"}),
    dict(geoid="48203", county="Harrison County", seat_word="Precinct",
         url="https://www.harrisoncountytexas.gov/page/CommissionerCourt", mode="name_below",
         label=r"Precinct (?P<n>[1-4])"),
    dict(geoid="48409", county="San Patricio County", seat_word="Precinct",
         url="https://www.sanpatriciocountytx.gov/page/comm.court.home", mode="inline",
         label=r"Commissioner Precinct (?P<n>[1-4]) - (?P<name>.+)"),
    dict(geoid="48497", county="Wise County", seat_word="Precinct",
         url="https://www.co.wise.tx.us/158/Commissioners-Court", mode="name_below",
         label=r"Commissioner Precinct (?P<n>[1-4]):"),
    dict(geoid="48427", county="Starr County", seat_word="Precinct",
         url="https://www.co.starr.tx.us/page/Commissioners.Court", mode="name_below",
         label=r"Precinct (?P<n>[1-4]) Commissioner"),
    dict(geoid="48347", county="Nacogdoches County", seat_word="Precinct",
         url="https://www.nacogdochesco.gov/178/County-Commissioners", mode="name_above",
         label=r"Precinct (?P<n>[1-4]) Commissioner"),
    dict(geoid="48221", county="Hood County", seat_word="Precinct",
         url="https://www.hoodcounty.texas.gov/government/county_commissioners/index.php",
         mode="name_above", label=LABEL,
         pages={1: "https://www.hoodcounty.texas.gov/government/county_commissioners/com_one.php",
                2: "https://www.hoodcounty.texas.gov/government/county_commissioners/com_two.php",
                3: "https://www.hoodcounty.texas.gov/government/county_commissioners/com_three.php",
                4: "https://www.hoodcounty.texas.gov/government/county_commissioners/com_four.php"}),
    dict(geoid="48467", county="Van Zandt County", seat_word="Precinct",
         url="https://www.vanzandtcounty.org/page/vanzandt.Commissioners.Court",
         mode="name_below", label=r"Precinct (?P<n>[1-4]) Commissioner"),
    dict(geoid="48001", county="Anderson County", seat_word="Precinct",
         url="https://www.andersoncountytx.gov/page/Commissioners.Court", mode="name_below",
         label=LABEL),
    dict(geoid="48473", county="Waller County", seat_word="Precinct",
         url="https://www.co.waller.tx.us/page/CommCourt.About", mode="inline",
         label=r"Precinct (?P<n>[1-4]) Commissioner - (?P<name>.+)",
         pages={1: "https://www.co.waller.tx.us/page/CommCourt.Precinct1",
                2: "https://www.co.waller.tx.us/page/CommCourt.Precinct2",
                3: "https://www.co.waller.tx.us/page/CommCourt.Precinct3",
                4: "https://www.co.waller.tx.us/page/CommCourt.Precinct4"}),
    dict(geoid="48199", county="Hardin County", seat_word="Precinct",
         url="https://www.hardincountytx.gov/page/CountyCommissioners", mode="inline",
         label=r"Pct\. (?P<n>[1-4]) (?P<name>.+)"),
    dict(geoid="48349", county="Navarro County", seat_word="Precinct",
         url="https://www.co.navarro.tx.us/page/Commissioners.Court",
         mode="name_below", label=r"Precinct (?P<n>[1-4]) Commissioner"),
    dict(geoid="48265", county="Kerr County", seat_word="Precinct",
         url="https://www.kerrcountytx.gov/kerr-county-all-departments/kerr-county-commissioners-court",
         mode="name_above", label=r"Kerr County Commissioner, Precinct (?P<n>[1-4])"),
    dict(geoid="48401", county="Rusk County", seat_word="Precinct",
         url="https://www.ruskcountytx.gov/page/Commissioners.Court",
         mode="name_below", label=r"Precinct (?P<n>[1-4]) Commissioner"),
    dict(geoid="48325", county="Medina County", seat_word="Precinct",
         url="https://www.medinatx.gov/page/Commissioners.Court", mode="name_below",
         label=r"(?=.*Commissioner)(?:Commissioner )?Precinct (?P<n>[1-4])(?: Commissioner)?"),
    dict(geoid="48073", county="Cherokee County", seat_word="Precinct",
         url="https://www.co.cherokee.tx.us/ips/cms/countyoffices/commissionersCourt.html",
         mode="name_below", label=r"Precinct (?P<n>[1-4]) Commissioner"),
    dict(geoid="48373", county="Polk County", seat_word="Precinct",
         url="https://www.polktx.gov/307/Commissioners-Court", mode="name_above",
         label=r", Precinct (?P<n>[1-4]), County Commissioner"),
    dict(geoid="48277", county="Lamar County", seat_word="Precinct",
         url="https://www.lamarcountytx.gov/page/Commissioners.Court",
         mode="name_above", label=r"Precinct (?P<n>[1-4]) Commissioner"),
    dict(geoid="48493", county="Wilson County", seat_word="Precinct",
         url="https://www.co.wilson.tx.us/page/wilson.Commissioners.Court", mode="name_below",
         label=r"Precinct (?P<n>[1-4]) Commissioner", offset=2, between="▲"),
    dict(geoid="48053", county="Burnet County", seat_word="Precinct",
         url="https://www.burnetcountytexas.org/1195/Elected-Officials",
         mode="name_above", label=r"Precinct (?P<n>[1-4]) Commissioner",
         pages={1: "https://www.burnetcountytexas.org/1378/Commissioner-Pct-1",
                2: "https://www.burnetcountytexas.org/1379/Commissioner-Pct-2",
                3: "https://www.burnetcountytexas.org/1380/Commissioner-Pct-3",
                4: "https://www.burnetcountytexas.org/1381/Commissioner-Pct-4"}),
    dict(geoid="48013", county="Atascosa County", seat_word="Precinct",
         url="https://co.atascosa.tx.us/commissioners/", mode="name_above",
         label=r"County Commissioner – Precinct (?P<n>[1-4])(?: \(Unexpired Term\))?"),
    dict(geoid="48465", county="Val Verde County", seat_word="Precinct",
         url="https://www.valverdecounty.texas.gov/", mode="name_below",
         label=r"Commissioner (?P<n>[1-4])"),
    dict(geoid="48071", county="Chambers County", seat_word="Precinct",
         url="https://www.chamberscountytx.gov/160/Commissioners-Court", mode="name_above",
         label=r"Commissioner Precinct (?P<n>[1-4])"),
    dict(geoid="48055", county="Caldwell County", seat_word="Precinct",
         url="https://www.co.caldwell.tx.us/page/Commissioners.Court",
         mode="name_below", label=r"Precinct (?P<n>[1-4]) Commissioner"),
    dict(geoid="48499", county="Wood County", seat_word="Precinct",
         url="https://www.mywoodcounty.com/page/commcourt_home", mode="name_below",
         label=r"Precinct (?P<n>[1-4]) Commissioner", offset=2, between="▲"),
    dict(geoid="48259", county="Kendall County", seat_word="Precinct",
         url="https://www.kendallcountytx.gov/m/directory/department?did=32", mode="name_above",
         label=r"Commissioner Precinct (?P<n>[1-4])"),
    dict(geoid="48097", county="Cooke County", seat_word="Precinct",
         url="https://www.co.cooke.tx.us/page/cooke.CommCourt",
         mode="name_below", label=r"Precinct (?P<n>[1-4]) Commissioner"),
    dict(geoid="48481", county="Wharton County", seat_word="Precinct",
         url="https://www.co.wharton.tx.us/page/wharton.Commissioners.Court", mode="inline",
         label=r"Commissioner (?P<name>.+), Pct\.? (?P<n>[1-4])"),
    dict(geoid="48459", county="Upshur County", seat_word="Precinct",
         url="https://www.countyofupshur.com/page/commissioners_court", mode="name_below",
         label=r"Commissioner Pct (?P<n>[1-4])"),
    dict(geoid="48249", county="Jim Wells County", seat_word="Precinct",
         url="https://www.co.jim-wells.tx.us/page/co.commissioners", mode="name_below",
         label=r"Commissioner - Precinct (?P<n>[1-4])",
         pages={1: "https://www.co.jim-wells.tx.us/page/co.pct.1.commissioner.page",
                2: "https://www.co.jim-wells.tx.us/page/co.pct.2.commissioner.page",
                3: "https://www.co.jim-wells.tx.us/page/co.pct.3.commissioner.page",
                4: "https://www.co.jim-wells.tx.us/page/co.pct.4.commissioner.page"}),
    dict(geoid="48049", county="Brown County", seat_word="Precinct",
         url="https://www.browncountytx.gov/page/brown.Commissioners.Court",
         mode="name_below", label=r"Precinct (?P<n>[1-4]) Commissioner"),
    dict(geoid="48223", county="Hopkins County", seat_word="Precinct",
         url="https://www.hopkinscountytx.org/page/hopkins.Commissioners.Court", mode="links",
         href=r"/page/hopkins\.Comm(?P<n>[1-4])$", skip=r"^Commissioners Court$"),
    dict(geoid="48321", county="Matagorda County", seat_word="Precinct",
         url="https://www.matagordatx.gov/page/Commissioners.Court", mode="name_below",
         label=r"Precinct (?P<n>[1-4]) Commissioner", offset=2, between="▲"),
    dict(geoid="48217", county="Hill County", seat_word="Precinct",
         url="https://www.co.hill.tx.us/page/hill.Commissioners.Court", mode="inline",
         label=r"Commissioner (?P<name>.+), Pct\.? (?P<n>[1-4])",
         pages={1: "https://www.co.hill.tx.us/page/hill.Commissioner.Pct1",
                2: "https://www.co.hill.tx.us/page/hill.Commissioner.Pct2",
                3: "https://www.co.hill.tx.us/page/hill.Commissioner.Pct3",
                4: "https://www.co.hill.tx.us/page/hill.Commissioner.Pct4"}),
    dict(geoid="48477", county="Washington County", seat_word="Precinct",
         url="https://www.co.washington.tx.us/page/washington.Commissioners.Court",
         mode="name_below", label=r"Precinct (?P<n>[1-4])", offset=2, between="▲",
         strip=r"^Commissioner "),
    dict(geoid="48147", county="Fannin County", seat_word="Precinct",
         url="https://www.co.fannin.tx.us/page/fannin.Commissioners.Court",
         mode="name_below", label=r"Precinct (?P<n>[1-4]) Commissioner"),
    dict(geoid="48227", county="Howard County", seat_word="Precinct",
         url="https://www.co.howard.tx.us/1215/Commissioners-Court",
         mode="name_above", label=r"Precinct (?P<n>[1-4]) Commissioner"),
    dict(geoid="48241", county="Jasper County", seat_word="Precinct",
         url="https://www.co.jasper.tx.us/page/Commissioners.Court",
         mode="name_above", label=r"Precinct (?P<n>[1-4]) Commissioner"),
    dict(geoid="48449", county="Titus County", seat_word="Precinct",
         url="https://www.co.titus.tx.us/page/co.commissioners", mode="name_below",
         label=r"Commissioner Precinct (?P<n>[1-4])"),
    dict(geoid="48025", county="Bee County", seat_word="Precinct",
         url="https://www.beecounty.texas.gov/169/Commissioners-Court",
         mode="name_above", label=r"Precinct (?P<n>[1-4]) Commissioner"),
    dict(geoid="48273", county="Kleberg County", seat_word="Precinct",
         url="https://www.co.kleberg.tx.us/page/kleberg.Commissioners.Court",
         mode="name_below", label=r"Precinct (?P<n>[1-4]) Commissioner"),
    dict(geoid="48015", county="Austin County", seat_word="Precinct",
         url="https://www.austincounty.com/page/austin.Commissioners.Court", mode="name_below",
         label=r"Commissioner, Precinct (?P<n>[1-4])"),
    dict(geoid="48185", county="Grimes County", seat_word="Precinct",
         url="https://grimescountytexas.gov/judge-precincts", mode="name_below",
         label=r"Commissioner Precinct (?P<n>[1-4])"),
    dict(geoid="48067", county="Cass County", seat_word="Precinct",
         url="https://www.co.cass.tx.us/page/cass.Commissioners.Court",
         mode="name_below", label=r"Precinct (?P<n>[1-4]) Commissioner"),
    dict(geoid="48363", county="Palo Pinto County", seat_word="Precinct",
         url="https://www.co.palo-pinto.tx.us/page/Commissioners.Court", mode="name_below",
         label=r"County Commissioner Precinct #(?P<n>[1-4])",
         pages={1: "https://www.co.palo-pinto.tx.us/page/Commissioner.Precinct.1",
                2: "https://www.co.palo-pinto.tx.us/page/Commissioner.Precinct.2",
                3: "https://www.co.palo-pinto.tx.us/page/Commissioner.Precinct.3",
                4: "https://www.co.palo-pinto.tx.us/page/Commissioner.Precinct.4"}),
    dict(geoid="48407", county="San Jacinto County", seat_word="Precinct",
         url="https://www.co.san-jacinto.tx.us/page/sanjacinto.Commissioners.Court",
         mode="name_above",
         label=r"(?:Commissioner, )?Precinct (?P<n>[1-4])(?: Commissioner)?",
         offset=2, between="Commissioner,", up_to=True),
    dict(geoid="48331", county="Milam County", seat_word="Precinct",
         url="https://www.milamcounty.net/government/commissioners.php", mode="name_below",
         label=r"Precinct (?P<n>[1-4])"),
    dict(geoid="48463", county="Uvalde County", seat_word="Precinct",
         url="https://www.uvaldecounty.gov/uvalde-county-commissioners", mode="name_below",
         label=r"COMMISSIONER, PRECINCT (?P<n>ONE|TWO|THREE|FOUR)"),
    dict(geoid="48149", county="Fayette County", seat_word="Precinct",
         url="https://www.co.fayette.tx.us/page/fayette.Commissioners.Court", mode="name_below",
         label=r"Precinct (?P<n>[1-4]) Commissioner"),
    dict(geoid="48419", county="Shelby County", seat_word="Precinct",
         url="https://www.co.shelby.tx.us/page/shelby.Commissioners.Court", mode="name_below",
         label=r"Precinct (?P<n>[1-4]) Commissioner", offset=4,
         between=r'"For all County Roads beginning(?: with [1-4]")?|with [1-4]"|▲', up_to=True),
    dict(geoid="48365", county="Panola County", seat_word="Precinct",
         url="https://www.co.panola.tx.us/1192/Commissioners-Court", mode="name_above",
         label=r"Precinct (?P<n>[1-4]) Commissioner"),
    dict(geoid="48293", county="Limestone County", seat_word="Precinct",
         url="https://www.co.limestone.tx.us/page/limestone.Commissioners.Court",
         mode="name_below", label=r"Precinct (?P<n>[1-4]) Commissioner"),
    dict(geoid="48225", county="Houston County", seat_word="Precinct",
         url="https://www.co.houston.tx.us/page/houston.Commissioners.Court", mode="name_below",
         label=r"Precinct (?P<n>[1-4]) Commissioner", offset=2, between="▲"),
    dict(geoid="48281", county="Lampasas County", seat_word="Precinct",
         url="https://www.co.lampasas.tx.us/page/lampasas.Commissioners.Court", mode="name_below",
         label=r"Precinct (?P<n>[1-4]) Commissioner"),
    dict(geoid="48219", county="Hockley County", seat_word="Precinct",
         url="https://www.co.hockley.tx.us/page/Commissioners.Court", mode="name_below",
         label=r"Precinct (?P<n>[1-4]) Commissioner"),
    dict(geoid="48341", county="Moore County", seat_word="Precinct",
         url="https://www.co.moore.tx.us/page/moore.Commissioners.Court", mode="name_below",
         label=r"Precinct (?P<n>[1-4]) Commissioner"),
    dict(geoid="48299", county="Llano County", seat_word="Precinct",
         url="https://www.llanocounty.gov/page/Commissioners.Court", mode="name_below",
         label=r"Precinct (?P<n>[1-4]) Commissioner"),
    dict(geoid="48179", county="Gray County", seat_word="Precinct",
         url="https://www.co.gray.tx.us/page/gray.Commissioners.Court", mode="name_below",
         label=r"Precinct (?P<n>[1-4]) Commissioner"),
    dict(geoid="48019", county="Bandera County", seat_word="Precinct",
         url="https://www.banderacounty.gov/page/cc.commissioners", mode="name_below",
         label=r"Precinct (?P<n>[1-4]) Commissioner"),
    dict(geoid="48233", county="Hutchinson County", seat_word="Precinct",
         url="https://www.co.hutchinson.tx.us/government/commissioners-court/", mode="name_above",
         label=r"Precinct (?P<n>[1-4]) Commiss?ioner"),
    dict(geoid="48089", county="Colorado County", seat_word="Precinct",
         url="https://www.co.colorado.tx.us/page/colorado.Commissioners.Court", mode="name_below",
         label=r"Commissioner, Precinct (?P<n>[1-4])"),
    dict(geoid="48285", county="Lavaca County", seat_word="Precinct",
         url="https://www.co.lavaca.tx.us/page/Commissioners.Court", mode="name_below",
         label=r"COMMISSIONER PRECINCT (?P<n>[1-4])", offset=2, between="▲"),
    dict(geoid="48489", county="Willacy County", seat_word="Precinct",
         url="https://www.willacy.gov/page/willacy.Commissioners.Court", mode="name_below",
         label=r"County Commissioner Precinct (?P<n>[1-4])", offset=2, between="▲"),
    dict(geoid="48337", county="Montague County", seat_word="Precinct",
         url="https://www.co.montague.tx.us/page/montague.Commissioners.Court", mode="name_below",
         label=r"Precinct (?P<n>[1-4]) Commissioner"),
    dict(geoid="48123", county="DeWitt County", seat_word="Precinct",
         url="https://www.co.dewitt.tx.us/page/Commissioners.Court", mode="name_above",
         label=r"Precinct (?P<n>[1-4]) Commissioner"),
    dict(geoid="48457", county="Tyler County", seat_word="Precinct",
         url="https://www.co.tyler.tx.us/page/tyler.Commissioners.Court", mode="name_below",
         label=r"Commissioner Pct\. (?P<n>[1-4])"),
    dict(geoid="48253", county="Jones County", seat_word="Precinct",
         url="https://www.co.jones.tx.us/page/jones.Commissioners.Court", mode="name_below",
         label=r"Precinct (?P<n>[1-4]) Commissioner"),
    dict(geoid="48161", county="Freestone County", seat_word="Precinct",
         url="https://www.co.freestone.tx.us/page/freestone.Commissioners.Court",
         mode="name_below", label=r"Precinct (?P<n>[1-4]) Commissioner"),
    dict(geoid="48003", county="Andrews County", seat_word="Precinct",
         url="https://www.co.andrews.tx.us/246/Commissioners-Court", mode="name_above",
         label=r", Pct\. (?P<n>[1-4])", strip="^Commissioner "),
    dict(geoid="48117", county="Deaf Smith County", seat_word="Precinct",
         url="https://www.co.deaf-smith.tx.us/page/deafsmith.Commissioners.Court",
         mode="name_below", label=r"Precinct (?P<n>[1-4]) Commissioner"),
    dict(geoid="48163", county="Frio County", seat_word="Precinct",
         url="https://www.co.frio.tx.us/page/co.commissioners-court", mode="name_below",
         label=r"Precinct (?P<n>[1-4]) Commissioner", offset=2, between="▲"),
    dict(geoid="48035", county="Bosque County", seat_word="Precinct",
         url="https://www.bosquecounty.gov/174/County-Commissioners", mode="name_above",
         label=r"Commissioner Precinct (?P<n>[1-4])"),
    dict(geoid="48503", county="Young County", seat_word="Precinct",
         url="https://www.co.young.tx.us/page/young.CommCourt", mode="name_below",
         label=r"YOUNG COUNTY COMMISSIONER PCT\. (?P<n>[1-4])"),
    dict(geoid="48133", county="Eastland County", seat_word="Precinct",
         url="https://newtools.cira.state.tx.us/page/eastland.Commissioners.Court",
         mode="name_below", label=r"Precinct (?P<n>[1-4])", offset=4, between=".+"),
    dict(geoid="48051", county="Burleson County", seat_word="Precinct",
         url="https://www.burlesoncountytx.gov/page/gov.commissioners", mode="inline",
         label=r"Precinct (?P<n>[1-4]) Commissioner ?- ?(?P<name>.+)"),
    dict(geoid="48287", county="Lee County", seat_word="Precinct",
         url="https://www.co.lee.tx.us/page/lee.Commissioners.Court", mode="name_below",
         label=r"Precinct (?P<n>[1-4]) Commissioner"),
    dict(geoid="48145", county="Falls County", seat_word="Precinct",
         url="https://www.co.falls.tx.us/page/Commissioners.Court", mode="name_below",
         label=r"Commissioner Precinct (?P<n>[1-4])"),
    dict(geoid="48415", county="Scurry County", seat_word="Precinct",
         url="https://www.co.scurry.tx.us/page/Commissioners.Court", mode="name_below",
         label=r"Precinct (?P<n>[1-4]) Commissioner"),
    dict(geoid="48395", county="Robertson County", seat_word="Precinct",
         url="https://www.co.robertson.tx.us/page/robertson.Commissioners.Court",
         mode="name_below", label=r"PRECINCT (?P<n>[1-4]), COMMISSIONER"),
    dict(geoid="48289", county="Leon County", seat_word="Precinct",
         url="https://www.co.leon.tx.us/page/leon.Commissioners.Court", mode="name_below",
         label=r"PRECINCT (?P<n>I|II|III|IV) COMMISSIONER"),
    dict(geoid="48371", county="Pecos County", seat_word="Precinct",
         url="https://www.co.pecos.tx.us/office/judge-commissioners/", mode="name_below",
         label=r"Precinct (?P<n>[1-4]) Commissioner"),
    dict(geoid="48239", county="Jackson County", seat_word="Precinct",
         url="https://www.co.jackson.tx.us/page/Commissioners.Court", mode="name_below",
         label=r"PRECINCT (?P<n>[1-4]) COMMISSIONER"),
    dict(geoid="48353", county="Nolan County", seat_word="Precinct",
         url="https://www.co.nolan.tx.us/page/nolan.Commissioners.Court", mode="name_below",
         label=r"Precinct (?P<n>[1-4]) Commissioner"),
    dict(geoid="48255", county="Karnes County", seat_word="Precinct",
         url="https://www.co.karnes.tx.us/page/karnes.Commissioners.CourtNew", mode="name_below",
         label=r"PRECINCT # (?P<n>[1-4]) COMMISSIONER"),
    dict(geoid="48505", county="Zapata County", seat_word="Precinct",
         url="https://www.co.zapata.tx.us/page/zapata.Commissioners.Court", mode="name_below",
         label=r"Precinct (?P<n>[1-4]) Commissioner", offset=2, between="▲"),
    dict(geoid="48059", county="Callahan County", seat_word="Precinct",
         url="https://newtools.cira.state.tx.us/page/callahan.Commissioners.Court",
         mode="name_below", label=r"Precinct (?P<n>[1-4]) Commissioner", offset=2, between="▲"),
    dict(geoid="48455", county="Trinity County", seat_word="Precinct",
         url="https://www.co.trinity.tx.us/page/trinity.Commissioners", mode="inline",
         label=r"(?P<name>.+) ~ PCT (?P<n>[1-4])"),
    dict(geoid="48313", county="Madison County", seat_word="Precinct",
         url="https://www.co.madison.tx.us/page/madison.Commissioners.Court", mode="name_below",
         label=r"Precinct (?P<n>[1-4]) Commissioner"),
    dict(geoid="48279", county="Lamb County", seat_word="Precinct",
         url="https://www.co.lamb.tx.us/page/Commissioners.Court", mode="name_above",
         label=r"Commissioner Precinct (?P<n>[1-4])"),
    dict(geoid="48487", county="Wilbarger County", seat_word="Precinct",
         url="https://www.co.wilbarger.tx.us/page/Commissioners.Court", mode="name_below",
         label=r"Commissioner Precinct (?P<n>[1-4])", offset=2, between="▲",
         strip="^Commissioner "),
    dict(geoid="48063", county="Camp County", seat_word="Precinct",
         url="https://www.co.camp.tx.us/page/camp.Commissioners.Court", mode="name_below",
         label=r"Precinct (?P<n>[1-4]) Commissioner"),
    dict(geoid="48115", county="Dawson County", seat_word="Precinct",
         url="https://www.co.dawson.tx.us/page/dawson.Commissioners.Court", mode="name_below",
         label=r"Precinct (?P<n>[1-4]) Commissioner"),
    dict(geoid="48351", county="Newton County", seat_word="Precinct",
         url="https://www.co.newton.tx.us/page/newton.Commissioners.Court", mode="name_below",
         label=r"Commissioner Precinct (?P<n>[1-4])"),
    dict(geoid="48379", county="Rains County", seat_word="Precinct",
         url="https://www.co.rains.tx.us/page/rains.Commissioners.Court", mode="name_below",
         label=r"Precinct (?P<n>[1-4]) Commissioner"),
    dict(geoid="48343", county="Morris County", seat_word="Precinct",
         url="https://www.co.morris.tx.us/page/morris.Commissioners.Court", mode="name_below",
         label=r"Precinct (?P<n>[1-4])"),
    dict(geoid="48445", county="Terry County", seat_word="Precinct",
         url="https://www.co.terry.tx.us/page/Commissioners.Court", mode="name_above",
         label=r"Precinct (?P<n>[1-4])"),
    dict(geoid="48475", county="Ward County", seat_word="Precinct",
         url="https://www.co.ward.tx.us/page/ward.Commissioners.Court", mode="name_below",
         label=r"Precinct (?P<n>[1-4]) Commissioner"),
    dict(geoid="48387", county="Red River County", seat_word="Precinct",
         url="https://www.co.red-river.tx.us/page/redriver.Commissioners.Court", mode="name_below",
         label=r"Precinct (?P<n>[1-4]) Commissioner"),
    dict(geoid="48031", county="Blanco County", seat_word="Precinct",
         url="https://www.blancocountytexas.gov/page/Commissioners.Court", mode="name_below",
         label=r"Precinct (?P<n>[1-4]) Commissioner"),
    dict(geoid="48297", county="Live Oak County", seat_word="Precinct",
         url="https://www.co.live-oak.tx.us/page/liveoak.Commissioners.Court", mode="name_below",
         label=r"Precinct (?P<n>[1-4]) Commissioner"),
    dict(geoid="48159", county="Franklin County", seat_word="Precinct",
         url="https://www.co.franklin.tx.us/page/franklin.Commissioners.Court", mode="name_below",
         label=r"Precinct (?P<n>[1-4]) Commissioner"),
]

_GATE = []
_LAST = {}


def gate():
    """One robots.txt reader for the run, with the client that fetches; it
    reads each host's file once."""
    if not _GATE:
        import requests  # the fetch below is requests too
        _GATE.append(RobotsGate(requests.Session(), UA_ROSTER_BOT, headers=UA_HEADERS_ROSTER_BOT))
    return _GATE[0]


def fetch(url, label):
    """One GET with this project's own client, after the host's robots.txt has
    been read with that same client and asked about this address. A refusal
    raises, so the county keeps its last record. Requests to one host are
    spaced by the Crawl-delay its robots.txt states, and by PACE_SECONDS where
    it states none (Lubbock's asks for 300 seconds). Returns bytes.

    It reads the policy through robots_policy.RobotsGate rather than
    scraper_common.require_robots_allowed or require_robots_once because
    those two end the process on a refusal, and here one county's refusal must
    keep that county's last record while the other counties are read; the gate
    also gives the Crawl-delay. Every address is asked about, not only the
    first on each host."""
    ok, why = gate().allows(url)
    print("robots.txt %s: %s" % (label, why), file=sys.stderr)
    if not ok:
        raise RuntimeError("%s refuses this client: %s; nothing fetched" % (url, why))
    host = urlsplit(url).hostname
    delay = max(PACE_SECONDS, float(gate().crawl_delay(url) or 0))
    wait = delay - (time.time() - _LAST.get(host, 0.0))
    if wait > 0:
        print("waiting %.0f s for %s's crawl delay" % (wait, host), file=sys.stderr)
        time.sleep(wait)
    try:
        return fetch_response(url, UA_HEADERS_ROSTER_BOT, timeout=60, attempts=2).content
    finally:
        _LAST[host] = time.time()


class Files(object):
    """Fetch, or read back, each page by a name derived from its URL."""

    def __init__(self, offline=None, save=None):
        self.offline = offline
        self.save = save

    @staticmethod
    def name(url):
        return re.sub(r"[^A-Za-z0-9._-]+", "_", url.split("://", 1)[-1])

    def get(self, url, label):
        name = self.name(url)
        for d in (self.offline, self.save):
            if d and os.path.exists(os.path.join(d, name)):
                with open(os.path.join(d, name), "rb") as f:
                    return f.read()
        if self.offline:
            raise RuntimeError("%s is not saved in %s" % (url, self.offline))
        body = fetch(url, label)
        if self.save:
            os.makedirs(self.save, exist_ok=True)
            with open(os.path.join(self.save, name), "wb") as f:
                f.write(body)
        return body


class Page(HTMLParser):
    """A page's visible text as lines, one per block, and its links as
    (href, text) pairs. Scripts, styles and inline SVG are dropped."""

    BLOCKS = {"p", "div", "li", "br", "h1", "h2", "h3", "h4", "h5", "h6", "tr", "td", "th",
              "span", "a", "strong", "section", "article", "header", "footer", "nav", "ul"}
    SKIP = {"script", "style", "noscript", "svg", "template"}

    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.skip = 0
        self.parts = []
        self.links = []
        self._href = None
        self._text = []
        self.feed(html)
        self.close()
        lines = (" ".join(l.split()) for l in "".join(self.parts).splitlines())
        self.lines = [l for l in lines if l]

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self.skip += 1
        if tag in self.BLOCKS:
            self.parts.append("\n")
        if tag == "a":
            self._href = dict(attrs).get("href") or ""
            self._text = []

    def handle_endtag(self, tag):
        if tag in self.SKIP:
            self.skip = max(0, self.skip - 1)
        if tag == "a" and self._href is not None:
            self.links.append((self._href, " ".join("".join(self._text).split())))
            self._href = None
        if tag in self.BLOCKS:
            self.parts.append("\n")

    def handle_data(self, data):
        if self.skip:
            return
        self.parts.append(data)
        if self._href is not None:
            self._text.append(data)


def person(raw, where):
    """A commissioner's name as printed, less a courtesy title, or raise."""
    name = HONORIFIC_RE.sub("", " ".join((raw or "").split()))
    problem = why_not_a_name(name) if name else "nothing printed"
    if problem:
        raise RuntimeError("%s: %r is not a name (%s)" % (where, name, problem))
    if NOT_A_PERSON_RE.search(name) or re.search(r"\d", name) or len(name) > 60:
        raise RuntimeError("%s: %r reads as an office or a page part, not a name" % (where, name))
    if not NAME_RE.match(name):
        raise RuntimeError("%s: %r is not shaped like a printed name" % (where, name))
    return name


def maybe_person(raw, where):
    """person(raw), or None: a line beside a label that is not a name (a menu
    heading, another label) is passed over rather than read."""
    try:
        return person(raw, where)
    except RuntimeError:
        return None


def agree(found, where):
    """{number: name} from a list of (number, name) readings, each number read
    at least once and every reading of it the same name."""
    out = {}
    for number, name in found:
        if number in out and out[number] != name:
            raise RuntimeError("%s: precinct %d is printed as both %r and %r"
                               % (where, number, out[number], name))
        out[number] = name
    return out


def number(token):
    return NUMBER_WORDS.get(token.upper()) or int(token)


def readings(page, spec, where, want=0):
    """Every (precinct, name) the page prints in the county's pattern. On a
    commissioner's own page (`want`, from `pages`) a label may name no
    precinct, as "Commissioner" alone does; the page's own precinct is used."""
    found = []
    lines = page.lines
    if spec.get("after"):
        try:
            lines = lines[lines.index(spec["after"]) + 1:]
        except ValueError:
            raise RuntimeError("%s: no %r heading" % (where, spec["after"]))
    mode = spec["mode"]
    if mode == "links":
        for href, text in page.links:
            m = re.search(spec["href"], href)
            if m and text and not re.match(spec["skip"], text):
                name = maybe_person(text, where)
                if name:
                    found.append((number(m.group("n")), name))
        return found
    label = re.compile("^%s$" % spec["label"])
    between = re.compile("^%s$" % spec["between"]) if spec.get("between") else None
    offset = spec.get("offset", 1)
    for i, line in enumerate(lines):
        m = label.match(line)
        if not m:
            continue
        if mode == "inline":
            raw = m.group("name")
        elif mode in ("name_above", "name_below"):
            step = -1 if mode == "name_above" else 1
            j = i + step * offset
            if spec.get("up_to") and between:
                j = i + step
                while abs(j - i) < offset and 0 <= j < len(lines) and between.match(lines[j]):
                    j += step
            if not 0 <= j < len(lines):
                continue
            gap = [lines[k] for k in range(i + step, j, step)]
            if gap and not (between and all(between.match(g) for g in gap)):
                continue
            raw = lines[j]
        else:
            raise RuntimeError("%s: unknown mode %r" % (where, mode))
        if spec.get("strip"):
            raw = re.sub(spec["strip"], "", raw)
        name = maybe_person(raw, where)
        if not name:
            continue
        n = m.groupdict().get("n")
        if n is None and spec.get("heading"):
            heading = re.compile("^%s$" % spec["heading"])
            above = (heading.match(lines[k]) for k in range(i - 1, -1, -1))
            hit = next((h for h in above if h), None)
            n = hit.group("n") if hit else None
        if n is None and not want:
            raise RuntimeError("%s: the label %r names no precinct" % (where, spec["label"]))
        found.append((number(n) if n is not None else want, name))
    return found


def read_county(spec, files):
    """The county's record, freshly read, or raise."""
    pages = spec.get("pages") or {0: spec["url"]}
    found = []
    for want, url in sorted(pages.items()):
        where = "%s (%s)" % (spec["county"], url)
        page = Page(files.get(url, spec["county"]).decode("utf-8", "replace"))
        got = readings(page, spec, where, want)
        if want:
            got = [(n, name) for n, name in got if n == want]
            if not got:
                raise RuntimeError("%s: no name printed for precinct %d" % (where, want))
        found.extend(got)
    where = "%s (%s)" % (spec["county"], spec["url"])
    names = agree(found, where)
    if sorted(names) != [1, 2, 3, 4]:
        raise RuntimeError("%s: read precincts %s, not 1 to 4" % (where, sorted(names)))
    if len(set(names.values())) != 4:
        raise RuntimeError("%s: the four names are not four people" % where)
    seats = []
    for n in (1, 2, 3, 4):
        seat = {"seat": "Commissioner, %s %d" % (spec["seat_word"], n), "number": n,
                "name": names[n]}
        if spec.get("pages"):
            seat["sourceUrl"] = spec["pages"][n]
        seats.append(seat)
    return {
        "county": spec["county"],
        "seats": seats,
        "source": "%s's own website" % spec["county"],
        "sourceUrl": spec["url"],
    }


def counties():
    """{GEOID: NAME} for the 254 counties the County layer draws."""
    with open(COUNTIES_FILE) as f:
        feats = json.load(f)["features"]
    return {str(f["properties"]["GEOID"]): str(f["properties"]["NAME"]) for f in feats}


def build(files, previous, today):
    out, carried, fresh, unread = {}, [], [], []
    for spec in COUNTIES:
        old = previous.get(spec["geoid"])
        try:
            rec = read_county(spec, files)
        except Exception as e:  # noqa: BLE001 -- any failure keeps the last record
            print("NOT READ: %s: %s" % (spec["county"], str(e)[:300]), file=sys.stderr)
            unread.append(spec["county"])
            if old:
                out[spec["geoid"]] = old
                carried.append(spec["county"])
            continue
        same = old and {k: v for k, v in old.items() if k != "asOf"} == rec
        rec["asOf"] = old["asOf"] if same else today
        out[spec["geoid"]] = rec
        fresh.append(spec["county"])
    return out, fresh, carried, unread


def shape_problems(data, drawn):
    problems = []
    listed = {c["geoid"]: c for c in COUNTIES}
    for geoid, rec in data.items():
        where = "%s (%s)" % (geoid, rec.get("county") if isinstance(rec, dict) else "?")
        if geoid not in drawn:
            problems.append("%s: not a county the County layer draws" % where)
            continue
        spec = listed.get(geoid)
        if not spec:
            problems.append("%s: not a county this builder reads" % where)
            continue
        if rec.get("county") != drawn[geoid] or rec.get("county") != spec["county"]:
            problems.append("%s: county name %r" % (where, rec.get("county")))
        if rec.get("sourceUrl") != spec["url"]:
            problems.append("%s: source address is not the county page this builder reads" % where)
        if rec.get("source") != "%s's own website" % spec["county"]:
            problems.append("%s: source %r" % (where, rec.get("source")))
        if not ISO_DATE_RE.match(str(rec.get("asOf", ""))):
            problems.append("%s: asOf %r is not a date" % (where, rec.get("asOf")))
        seats = rec.get("seats")
        if not isinstance(seats, list) or [s.get("number") for s in seats] != [1, 2, 3, 4]:
            problems.append("%s: seats are not precincts 1 to 4 in order" % where)
            continue
        names = []
        for s in seats:
            want = "Commissioner, %s %d" % (spec["seat_word"], s["number"])
            if s.get("seat") != want:
                problems.append("%s: seat %r, not %r" % (where, s.get("seat"), want))
            page = (spec.get("pages") or {}).get(s["number"])
            if s.get("sourceUrl") != page or set(s) - {"seat", "number", "name", "sourceUrl"}:
                problems.append("%s: seat %d's fields or page address" % (where, s["number"]))
            try:
                names.append(person(s.get("name"), where))
            except RuntimeError as e:
                problems.append(str(e))
        if len(set(names)) != 4:
            problems.append("%s: the four names are not four people" % where)
        if set(rec) != {"county", "seats", "source", "sourceUrl", "asOf"}:
            problems.append("%s: fields %s" % (where, sorted(rec)))
    return problems


def load(path):
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def check():
    data = load(os.path.join(DEFAULT_OUT_DIR, OUT_NAME))
    if not data:
        print("FAIL: %s is missing or empty" % OUT_NAME, file=sys.stderr)
        sys.exit(1)
    problems = shape_problems(data, counties())
    for p in problems:
        print("FAIL: %s" % p, file=sys.stderr)
    if problems:
        sys.exit(1)
    print("tx-county-commissioners: OK — %d counties, %d commissioners named from the counties' "
          "own websites (%s)" % (len(data), 4 * len(data),
                                ", ".join(sorted(r["county"] for r in data.values()))))


def main(argv):
    args = list(argv)
    if "--check" in args:
        check()
        return
    opts = {}
    for flag in ("--save", "--offline", "--unread"):
        if flag in args:
            i = args.index(flag)
            opts[flag] = args[i + 1]
            del args[i:i + 2]
    save, offline = opts.get("--save"), opts.get("--offline")
    out_dir = args[0] if args else DEFAULT_OUT_DIR
    path = os.path.join(out_dir, OUT_NAME)
    previous = load(path)
    today = datetime.date.today().isoformat()
    data, fresh, carried, unread = build(Files(offline=offline, save=save), previous, today)
    if opts.get("--unread"):
        with open(opts["--unread"], "w", encoding="utf-8") as f:
            f.write("".join(c + "\n" for c in unread))
    if not data:
        raise SystemExit("No county was read and none was shipped before; nothing written.")
    problems = shape_problems(data, counties())
    if problems:
        for p in problems:
            print("FAIL: %s" % p, file=sys.stderr)
        raise SystemExit("Refusing to write %s" % path)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(dict(sorted(data.items())), f, indent=1, ensure_ascii=False)
        f.write("\n")
    print("Wrote %s (%d counties: %d read now%s)"
          % (path, len(data), len(fresh),
             ", carried: " + ", ".join(carried) if carried else ""))


if __name__ == "__main__":
    main(sys.argv[1:])
