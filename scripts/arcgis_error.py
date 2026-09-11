#!/usr/bin/env python3
"""Raise on an ArcGIS error that arrived as HTTP 200.

ArcGIS REST reports failures IN THE BODY: the response is 200 with an `error`
member carrying the code and message. `raise_for_status()` cannot see it, so a
caller that goes straight to `.json()` reads an error payload as data. What that
looks like downstream depends on the caller and none of it looks like an outage:

  * a caller doing `payload.get("features", [])` gets an empty list and reports
    the county as having nothing;
  * a caller doing `payload["features"]` gets a KeyError, which is loud but
    blames the wrong thing;
  * a caller that already degrades gracefully on `requests.RequestException`
    never reaches its own handler, because nothing was raised.

That last one is why this raises a RequestException SUBCLASS: a script that
already writes `except requests.RequestException` to fall back keeps working,
unchanged, for this failure too.

Measured case, 2026-09-08: build_logan_park_districts.py reported "layer 26
returned 0 features, expected exactly 1" when the service had actually answered
"API calls quota exceeded (6958 request units)! maximum allowed request units
(6000) per Minute" — a message that blamed a county's data for our own request
rate. A 429 clears on its own, so callers that retry should treat `is_rate_limit`
as the retryable case.

THE SURFACE, measured 2026-09-08 across the 43 scripts in scripts/ that call an
ArcGIS REST endpoint, and what is and is not fixed here:

  6 read the `error` member themselves already (build_mcdonough_precincts,
    build_parcel_fabric_districts, build_stclair_precinct_polling,
    lake_municipal_officials_scraper, vtd_board_districts,
    winnebago_municipal_officials_scraper).

  6 are the callers this module was written for, and they are the ones where
    an error payload was NOT caught at all or was reported as health:
      tazewell_county_board_scraper   — the only silent one. Its GIS read is a
        cross-check wrapped in `except requests.RequestException` to warn and
        carry on, so nothing raised meant no warning: districts went unfilled
        and the run reported success.
      validate_sources.check_endpoints — asked only the status code, so all 43
        endpoints answering 200-with-error read as "endpoint reachable". This
        is the gate whose job is to say whether a source is healthy.
      peoria_county_board_scraper, build_municipal_ward_coverage,
      boone_municipal_officials_scraper, build_logan_park_districts — stop, but
        named the wrong cause.

  31 stop on a count guard and are NOT changed here. Nothing wrong ships: the
    ArcGIS response is the builder's whole output, so zero features means the
    floor refuses the write. What they lose is the diagnosis — a weekly refresh
    fails with "expected exactly 7 districts, got 0", which sends a reader to
    the county's website when the answer was to wait a minute. 27 of the 31 are
    on weekly workflows; none is on the PR path (build_metro_outline --check and
    isbe_precinct_fabric --selftest both read shipped files and do not fetch).
    Routing those 31 through this module is the follow-up.
"""

# The base is requests.RequestException WHERE REQUESTS IS AVAILABLE, so that a
# caller which already writes `except requests.RequestException` to degrade
# gracefully keeps working unchanged for this failure too. Not every ArcGIS
# caller here uses requests — build_municipal_ward_coverage.py is on urllib —
# so the import is optional and the base falls back to RuntimeError. Either way
# it is an Exception and nothing silently returns an error payload as data.
try:
    from requests import RequestException as _Base
except Exception:                                  # pragma: no cover - no requests
    _Base = RuntimeError


class ArcGISServiceError(_Base):
    """An ArcGIS error object returned with HTTP 200."""

    def __init__(self, code, message, details, what):
        self.code = code
        self.arcgis_message = message
        self.details = details or []
        detail = "; ".join(str(d) for d in self.details)
        super().__init__(
            "%s: ArcGIS returned error %s — %s%s"
            % (what, code, message, (" (%s)" % detail) if detail else ""))

    @property
    def is_rate_limit(self):
        return self.code == 429


def raise_for_arcgis_error(payload, what="the ArcGIS service"):
    """Raise ArcGISServiceError if `payload` is an ArcGIS error object.

    Returns the payload otherwise, so it can wrap a parse inline:
        rows = raise_for_arcgis_error(r.json(), "Peoria's roster layer")
    """
    if isinstance(payload, dict):
        err = payload.get("error")
        if isinstance(err, dict):
            raise ArcGISServiceError(err.get("code"), err.get("message", ""),
                                     err.get("details"), what)
    return payload
