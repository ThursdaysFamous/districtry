"""One module per Tennessee county whose commission this project names.

A COUNTY JOINS BY HAVING A MODULE HERE, and nothing else lists them:
tn_commissioner_scraper.py discovers every module in this package, so there is
no second table to keep in step. Each module states, from the county's own page
on the day the parser was written:

  COUNTY, FIPS   the county's name and its three-digit code
  DOMAINS        the county's own web and e-mail domains; an e-mail or a
                 profile link off them is never kept
  URLS           the pages to read, the roster page first
  SOURCE_URL     the page a reader is linked to, where it is not URLS[0]
  SEATS          seats per district as the county elects them, a vacant seat
                 included
  AT_LARGE       the seats elected countywide
  PHONES         True only where every phone the parser keeps is a government
                 office line (default False)
  TITLE, BODY    what the county calls a member and the body, where that is not
                 "Commissioner" of the "County Commission" (text only: a
                 pattern of the parser's own takes another name)
  DISTRICT_LABELS  the county's own name for each district, keyed by the
                 state's district number, where the county does not call its
                 districts by those numbers ({"1": "District A", ...}); every
                 district or none, each name different, and the module's
                 docstring says how the pairing was MEASURED, never assumed
  parse(pages)   {url: page text, HTML comments removed} ->
                 {"districts": {"1": [member, ...]}, "atLarge": [member, ...]}

and its docstring records what its names were checked against before it
joined: that county's results of the 6 August 2026 election where a government
host serves them to us, and otherwise the county's own documents from after the
new term began on 1 September 2026, named one by one, with what they did not
establish said plainly. A module whose name
starts with an underscore is shared code, not a county.
"""
