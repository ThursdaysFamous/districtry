#!/usr/bin/env python3
"""The seven Texas counties whose commissioners are read with a browser
identity, and the one reader that does it.

build_tx_county_commissioners.py reads every other county with this project's
own client. These seven refuse that client, on both HTTP stacks, at the page
and at robots.txt alike, and serve the fourth rung of
scripts/probe_user_agents.py: the standard-library stack sending Chrome/126
and its client hints (scraper_common.UA_HINTS_CHROME_126). CLAUDE.md allows a
browser string only where a site measurably refuses ours, with the
measurement recorded in the calling file, and Adam said yes to it for these
counties on 2026-11-17.

They live in a file of their own so that this is the only Texas file sending
a browser string, and the only hosts it reaches are these seven. A browser
string in the builder itself would have counted every county site it reads
as reached by one.

Measured 2026-11-17 by scripts/probe_user_agents.py at the exact page each
spec below reads, and recorded in user-agent-measurements.json as
token-refused-and-stack (requests + token, stdlib + token and requests +
Chrome answer HTTP 403; stdlib + Chrome answers the page):

  Williamson  www.wilcotx.gov               Cloudflare "Sorry, you have been blocked"
  Hays        www.hayscountytx.gov          Cloudflare "Sorry, you have been blocked"
  McLennan    www.mclennan.gov              Cloudflare "Sorry, you have been blocked"
  Brazoria    www.brazoriacountytx.gov      Akamai "Access Denied"
  Galveston   www.galvestoncountytx.gov     Akamai "Access Denied"
  Johnson     www.johnsoncountytx.org       Akamai "Access Denied"
  Nueces      www.nuecesco.com              Akamai "Access Denied"

Read with this rung, every one serves its robots.txt and it permits these
pages. The three Cloudflare hosts state a Crawl-delay of 10 seconds, which
the builder honours. None of the seven answers with a challenge page to this
rung; a host that ever does is an access control, and nothing here works
around one.

Not here: Reeves (www.reevescounty.org) also refuses the token and serves
this rung, but prints its four seats in three different layouts, so no one
rule reads it; the builder's docstring records it.
"""

import os
import sys
import time
import urllib.error
from urllib.parse import urlsplit

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(_HERE)), "scripts"))
from robots_policy import RobotsGate  # noqa: E402  (FLEET_SHARED)
from scraper_common import UA_HINTS_CHROME_126, fetch_stdlib  # noqa: E402  (FLEET_SHARED)

# Each entry is a COUNTIES entry in the builder's shape (see its comment above
# COUNTIES for the modes and options); the builder appends these to its list.
BROWSER_COUNTIES = [
    dict(geoid="48491", county="Williamson County", seat_word="Precinct", client="browser",
         url="https://www.wilcotx.gov/331/Commissioners-Court", mode="inline",
         split=r",\s+(?=(?:Commissioner|County Judge)\b)",
         label=r"Commissioner Pct\. (?P<n>[1-4]) (?P<name>.+)"),
    dict(geoid="48039", county="Brazoria County", seat_word="Precinct", client="browser",
         url="https://www.brazoriacountytx.gov/government/commissioners-court", mode="inline",
         label=r"Commissioner (?P<name>.+)",
         pages={n: "https://www.brazoriacountytx.gov/government/commissioners-court/"
                   "commissioner-precinct-%d" % n for n in (1, 2, 3, 4)}),
    dict(geoid="48355", county="Nueces County", seat_word="Precinct", client="browser",
         url="https://www.nuecesco.com/commissioners-court", mode="name_below", label=r"Print",
         pages={1: "https://www.nuecesco.com/commissioners-court/commissioner-precinct-1/"
                   "commissioner-pusley",
                2: "https://www.nuecesco.com/commissioners-court/commissioner-precinct-2/"
                   "commissioner-gonzalez",
                3: "https://www.nuecesco.com/commissioners-court/commissioner-precinct-3/"
                   "commissioner-marez",
                4: "https://www.nuecesco.com/commissioners-court/commissioner-precinct-4/"
                   "commissioner-chesney"}),
    dict(geoid="48167", county="Galveston County", seat_word="Precinct", client="browser",
         url="https://www.galvestoncountytx.gov/our-county/county-judge/commissioners-court",
         mode="name_below", label=r"Commissioner Precinct (?P<n>[1-4])",
         strip=r"^,\s+"),
    dict(geoid="48309", county="McLennan County", seat_word="Precinct", client="browser",
         url="https://www.mclennan.gov/", mode="name_above",
         label=r"Precinct (?P<n>[1-4]) Commissioner"),
    dict(geoid="48209", county="Hays County", seat_word="Precinct", client="browser",
         url="https://www.hayscountytx.gov/188/Commissioners-Court-Members",
         mode="name_below", label=r"Contact Us",
         pages={1: "https://www.hayscountytx.gov/192/Precinct-1-Commissioner",
                2: "https://www.hayscountytx.gov/193/Precinct-2-Commissioner",
                3: "https://www.hayscountytx.gov/194/Precinct-3-Commissioner",
                4: "https://www.hayscountytx.gov/195/Precinct-4-Commissioner"}),
    dict(geoid="48251", county="Johnson County", seat_word="Precinct", client="browser",
         url="https://www.johnsoncountytx.org/government/commissioners", mode="inline",
         label=r"(?:The\s+)?Honorable (?P<name>.+)",
         pages={n: "https://www.johnsoncountytx.org/government/commissioners/"
                   "commissioner-precinct-%d" % n for n in (1, 2, 3, 4)}),
]

BROWSER_HOSTS = frozenset(urlsplit(c["url"]).hostname for c in BROWSER_COUNTIES)


def browser_gate():
    """A robots.txt reader for this rung: the same stack and headers that
    fetch, so the policy read is the one that binds the crawl."""
    return RobotsGate(None, UA_HINTS_CHROME_126["User-Agent"], headers=UA_HINTS_CHROME_126)


def fetch_browser(url, delay):
    """One GET on this rung, tried a second time after a dropped connection or
    a 429 (waiting at least 60 seconds for the 429), never after any other
    refusal. Only the seven hosts above are read this way. Returns bytes."""
    host = urlsplit(url).hostname
    if host not in BROWSER_HOSTS:
        raise RuntimeError("%s is not one of the counties measured for this rung" % host)
    for attempt in (1, 2):
        try:
            return fetch_stdlib(url, headers=UA_HINTS_CHROME_126, timeout=60).encode("utf-8")
        except urllib.error.HTTPError as e:
            if e.code != 429 or attempt == 2:
                raise
            time.sleep(max(60.0, delay))
        except (urllib.error.URLError, OSError):
            if attempt == 2:
                raise
            time.sleep(max(10.0, delay))
