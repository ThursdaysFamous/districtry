"""Rutherford County Commission: 21 commissioners, one from each of Districts
1-21. The county's main site (rutherfordcountytn.gov, where the commission's
and the election commission's pages live) refuses this client by robots.txt,
so it is not read. The source is the county's own GIS host
(maps.rutherfordcountytn.gov, no robots.txt), service
Election/Election_Commission, layer 5 "Commission Districts": one feature per
district carrying DISTRICT (1-21), NAME (the commissioner) and NUMCOMS (the
number of commissioners the district elects). The district and the name are
two fields of the SAME feature, so nothing is read from order; NUMCOMS must be
1 on every row, which is what makes each district a single-member seat.

The URL carries its whole query string in the literal (returnGeometry=false,
f=json), so parse() receives the JSON text. An ArcGIS error object, a
transfer-limit flag, a missing or repeated district, or a blank name raises.

Currency WAS checked, against the Rutherford County Election Commission's
own summary of the 6 August 2026 county general election, served from
secured.rutherfordcountytn.gov (a different host from the refused main site,
whose robots.txt has no rule matching the results path; read 2026-10-11 with
this project's own client): all 21 seats were on that ballot, and the winner
of every district is the name this layer carries for it (the layer writes
"Robert Peay" and "Carl B. Boyd" where the results print "Robert Peay Jr." and
"Carl Boyd"). The layer's own edit dates agree: eight rows were edited on
2026-08-31, the day before the new terms began.

No e-mail, phone or profile link is published in the layer, so none is
recorded."""
import json
from ._common import member, vacant

COUNTY = "Rutherford"; FIPS = "149"
DOMAINS = ("rutherfordcountytn.gov",)
# ONE literal, never split across lines: the fleet's user-agent probe reads URL
# literals out of the file, and a split one is measured at its first half.
URLS = ["https://maps.rutherfordcountytn.gov/server/rest/services/Election/Election_Commission/MapServer/5/query?where=1%3D1&outFields=DISTRICT,NAME,NUMCOMS,last_edited_date&returnGeometry=false&orderByFields=DISTRICT&f=json"]  # noqa: E501
# What a reader is linked to: the layer's own description page on the county's
# GIS host, rather than the JSON query above.
SOURCE_URL = "https://maps.rutherfordcountytn.gov/server/rest/services/Election/Election_Commission/MapServer/5"
SEATS = {str(i): 1 for i in range(1, 22)}
AT_LARGE = 0


def parse(pages):
    data = json.loads(pages[URLS[0]])
    if "error" in data:
        raise ValueError("ArcGIS answered an error, not features: %r" % (data["error"],))
    if data.get("exceededTransferLimit"):
        raise ValueError("the query hit the transfer limit; rows are missing")
    feats = data.get("features")
    if not feats:
        raise ValueError("no features in the Commission Districts answer")
    districts = {}
    for f in feats:
        a = f.get("attributes") or {}
        d, name, num = a.get("DISTRICT"), (a.get("NAME") or "").strip(), a.get("NUMCOMS")
        if not isinstance(d, int) or not 1 <= d <= 99:
            raise ValueError("a row with no usable DISTRICT: %r" % (a,))
        if num != 1:
            raise ValueError("District %s: NUMCOMS is %r, not 1" % (d, num))
        key = str(d)
        if key in districts:
            raise ValueError("District %s appears twice" % key)
        if not name:
            raise ValueError("District %s: NAME is blank (the layer does not say vacant)" % key)
        if name.lower() in ("vacant", "vacancy"):
            districts[key] = [vacant()]
        else:
            districts[key] = [member(name)]
    return {"districts": districts, "atLarge": []}
