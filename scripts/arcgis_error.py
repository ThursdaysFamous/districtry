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

SECOND MEASURED CASE, 2026-09-28, and it is why `is_rate_limit` no longer asks the
code alone. update-il-special-district-officials run 5 aborted a 486-unit weekly
refresh twelve seconds in, on
    {"error": {"message": "Unable to perform query. Too many requests."}}
from services.arcgis.com. The caller printed the message and not the code, so
whether that envelope ALSO carried 429 is UNOBSERVED — and the same is true of the
Logan case above. So a code-only reading cannot be relied on for either of the two
rate limits this project has actually met, and neither can a message-only one:
Logan's wording contains no "too many requests" and Hamilton's contains no
"quota". Both signals are read, and each wording is quoted from the run that
produced it rather than guessed at.

`retry_rate_limited` is the bounded ladder for it, and it is bounded on purpose: a
persistent limit must FAIL a run rather than stall it. It takes a fetch callable
instead of a URL, because this module deliberately has no fetch stack — its
callers are split between `requests` and `urllib` — and it retries an HTTP 429 as
well, which is not a new policy but `scraper_common.fetch()`'s existing one
reaching the urllib callers that never had it.

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

WHAT THE 2026-09-28 CASE ADDED TO THAT SURVEY: the survey was complete when it was
made, and the next fork arrived after it. il_special_district_officials_scraper.py
was created 2026-09-11 (#857) and grew its OWN `error` read the same day (#858),
three days after this module existed — so it appears in neither list above, and it
is the shape `validate_workflow_deps.FLEET_SHARED` exists to prevent: a second
answer to "what is an ArcGIS error", in the same tree rather than per instance. It
is routed through here now.

NOTHING GATES THAT, and the absence is stated rather than implied. FLEET_SHARED is
prose; no check fails when a new caller reads `payload["error"]` itself. Sweeping
the fleet for files that read an `error` member and do not import this module finds
several whose first commit postdates 2026-09-08 — scripts/il_gis_board_scraper.py
(09-15), scripts/build_block_population.py (09-23), scripts/mirror_tiger_tiles.py
(09-27) and mi/scripts/build_mi_returns_roster.py (09-22) among them — but that
sweep also matches error members that have nothing to do with ArcGIS, and most of
the tree shares one early commit date, so it is a CANDIDATE LIST to read one by
one and never a count. Two of those four query TIGERweb and do read the envelope
correctly; what none of them shares is this module's rate-limit reading.
"""

import re
import sys
import time

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
        return self.code == 429 or bool(
            _RATE_LIMIT_WORDING.search(self.arcgis_message or ""))


# The wordings measured on the two rate limits this project has met, each quoted
# from the run that produced it (see the module docstring). A vendor's English can
# move, which is why the code is still read too; and a message merely naming
# "requests" is not a rate limit, which is why these are phrases and not words.
_RATE_LIMIT_WORDING = re.compile(
    r"too many requests"                       # Hamilton fire, 2026-09-28
    r"|quota exceeded"                         # Logan layer 26, 2026-09-08
    r"|maximum allowed request units",         # the same message, its second half
    re.I)

# Waits before re-asking. Four attempts and 65s at worst; a limit that outlasts
# them is raised, never waited on further.
RATE_LIMIT_BACKOFF = (5.0, 15.0, 45.0)


def _http_status(exc):
    """The HTTP status an exception carries, on either stack, else None."""
    code = getattr(exc, "code", None)              # urllib.error.HTTPError
    if isinstance(code, int):
        return code
    return getattr(getattr(exc, "response", None), "status_code", None)


def retry_rate_limited(fetch, what="the ArcGIS service",
                       backoff=RATE_LIMIT_BACKOFF, sleep=time.sleep):
    """`fetch()`'s value, re-asking ONLY a rate limit.

    `fetch` is a no-argument callable that performs the request and parses it —
    normally ending in `raise_for_arcgis_error(...)`, so a rate limit arrives here
    as an ArcGISServiceError. An HTTP 429 from either stack is re-asked too. EVERY
    OTHER FAILURE PROPAGATES ON THE FIRST ANSWER: a name list a caller cannot read
    is not a source that stopped publishing, and smoothing the two together is how
    a thinner payload ships. A 5xx is deliberately not retried here — it has not
    been an observed condition on these services, and widening this to every
    transient would re-open that distinction.

    Each re-ask is reported to stderr, so a run that only just got through says
    so rather than looking like a clean week.
    """
    for wait in tuple(backoff) + (None,):
        try:
            return fetch()
        except Exception as exc:                   # noqa: BLE001 (re-raised below)
            limited = (getattr(exc, "is_rate_limit", False)
                       or _http_status(exc) == 429)
            if not limited or wait is None:
                # Giving up on a LIMIT is said out loud: the exception carries
                # the service's message and not the fact that the ladder was
                # spent, so without this line a reader of the log cannot tell a
                # first-answer refusal from four.
                if limited:
                    print("  RATE LIMITED: %s — gave up after %d attempt(s)"
                          % (what, len(tuple(backoff)) + 1), file=sys.stderr)
                raise
            print("  RATE LIMITED: %s — %s, re-asking in %.0fs"
                  % (what, _rate_limit_reason(exc), wait), file=sys.stderr)
            sleep(wait)


def _rate_limit_reason(exc):
    return getattr(exc, "arcgis_message", None) or ("HTTP %s" % _http_status(exc))


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


def _selftest():
    """Prove the rate-limit reading and the ladder, both directions.

    The reading is what decides whether a weekly refresh waits a minute or
    abandons a county, and the ladder runs ONLY in the rare condition it exists
    for — so a defect in either would surface weeks later, in a job nobody is
    watching, as a county that stopped being covered.
    """
    fails = []

    def ok(label, got, want):
        if got != want:
            fails.append("%s\n     got  %r\n     want %r" % (label, got, want))

    def limited(code, message):
        try:
            raise_for_arcgis_error({"error": {"code": code, "message": message}})
        except ArcGISServiceError as exc:
            return exc.is_rate_limit
        return "did not raise"

    # 1. THE READING. Both measured wordings, the code, and the two ways it must
    #    say no: an ordinary shape error, and a message that merely mentions
    #    requests (which an over-broad pattern would swallow).
    ok("no error member returns the payload",
       raise_for_arcgis_error({"features": []}), {"features": []})
    ok("a non-dict error member is not an envelope",
       raise_for_arcgis_error({"error": "nope"}), {"error": "nope"})
    ok("Hamilton's wording, 2026-09-28",
       limited(None, "Unable to perform query. Too many requests."), True)
    ok("Logan's wording, 2026-09-08",
       limited(None, "API calls quota exceeded (6958 request units)! maximum "
                     "allowed request units (6000) per Minute"), True)
    ok("the wording is matched whatever its case",
       limited(500, "TOO MANY REQUESTS"), True)
    ok("a 429 carries it with no wording at all", limited(429, ""), True)
    ok("a shape error is not a rate limit",
       limited(400, "Unable to complete operation."), False)
    ok("a message merely naming requests is not a rate limit",
       limited(400, "Invalid or missing input requests."), False)

    # 2. THE LADDER. `sleep` is captured rather than stubbed away, so the DEFAULT
    #    waits are asserted and not only the number of re-asks.
    class _Http429(Exception):
        code = 429

    class _Http404(Exception):
        code = 404

    def drive(script, want_text=False, **kw):
        """(value or the exception raised, the waits taken, re-asks reported)."""
        waits, it = [], iter(script)

        def fetch():
            nxt = next(it)
            if isinstance(nxt, Exception):
                raise nxt
            return raise_for_arcgis_error(nxt, "hamilton fire")

        err, real = _Captured(), sys.stderr
        sys.stderr = err
        try:
            got = retry_rate_limited(fetch, "hamilton fire",
                                     sleep=waits.append, **kw)
        except Exception as exc:                   # noqa: BLE001 (asserted below)
            got = exc
        finally:
            sys.stderr = real
        reasks = [l for l in err.text.splitlines()
                  if "RATE LIMITED" in l and "gave up" not in l]
        if want_text:
            return got, waits, len(reasks), err.text
        return got, waits, len(reasks)

    good = {"features": [{"attributes": {"NAME": "DAHLGREN FIRE DISTRICT"}}]}
    limit = {"error": {"message": "Unable to perform query. Too many requests."}}
    shape = {"error": {"code": 400, "message": "Unable to complete operation."}}

    got, waits, reasks = drive([limit, good])
    ok("one limit then success: the payload", got, good)
    ok("one limit then success: the first wait", waits, [5.0])
    ok("one limit then success: one re-ask", reasks, 1)

    got, waits, reasks = drive([_Http429(), good])
    ok("an HTTP 429 is re-asked too", got, good)
    ok("an HTTP 429: one wait", waits, [5.0])

    got, waits, reasks = drive([limit] * 4)
    ok("a limit that outlasts the ladder raises",
       isinstance(got, ArcGISServiceError), True)
    ok("the whole default ladder was taken", waits, [5.0, 15.0, 45.0])
    ok("every re-ask was reported", reasks, 3)
    got, waits, reasks, said = drive([limit] * 4, want_text=True)
    ok("giving up on a limit says the ladder was spent",
       "gave up after 4 attempt(s)" in said, True)

    # THE GUARD THAT NOTHING WAS SOFTENED. Each of these scripts carries MORE
    # answers than correct code consumes: code that wrongly re-asked would
    # otherwise run the iterator out and crash, which reads as a broken selftest
    # rather than as the wrong behaviour it is.
    got, waits, reasks = drive([shape] * 4)
    ok("a shape error raises on the first answer",
       isinstance(got, ArcGISServiceError), True)
    ok("a shape error is never waited on", waits, [])

    got, waits, reasks = drive([_Http404()] * 4)
    ok("a 404 propagates untouched", isinstance(got, _Http404), True)
    ok("a 404 is never waited on", waits, [])

    if fails:
        print("arcgis-error selftest: FAIL", file=sys.stderr)
        for f in fails:
            print("  - %s" % f, file=sys.stderr)
        return 1
    print("arcgis-error selftest: OK — both measured rate-limit wordings and a "
          "429 read as retryable, a shape error and a stray mention of requests "
          "do not; the ladder takes 5/15/45 and then raises, and never waits on "
          "a shape error or a 404")
    return 0


class _Captured:
    """Minimal stderr stand-in for the selftest (no io import at module scope)."""

    def __init__(self):
        self.text = ""

    def write(self, s):
        self.text += s
        return len(s)

    def flush(self):
        pass


if __name__ == "__main__":
    if "--selftest" in sys.argv[1:]:
        raise SystemExit(_selftest())
    raise SystemExit("arcgis-error: this module is imported, not run "
                     "(only --selftest does anything)")
