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
                 "Commissioner" of the "County Commission"
  parse(pages)   {url: page text, HTML comments removed} ->
                 {"districts": {"1": [member, ...]}, "atLarge": [member, ...]}

and its docstring records how its names were checked against that county's
results of the 6 August 2026 election before it joined. A module whose name
starts with an underscore is shared code, not a county.
"""
