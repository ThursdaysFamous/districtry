#!/usr/bin/env python3
"""Diagnostic: prove the GOOGLE_SA_KEY secret can actually read Search Console
(and, if its numeric id is supplied, GA4) — and report what it can see.

WHY THIS IS A WORKFLOW AND NOT A LOCAL SCRIPT. A GitHub Actions secret is
write-only: it cannot be read back through the API, and it does not exist in a
developer sandbox. The only way to verify one is to run something where it is
mounted. So this runs in Actions and prints its findings to the job log.

WHAT IT DELIBERATELY NEVER PRINTS: the key, any field of the key, or the bearer
token minted from it. A credential check whose own output leaks the credential
has made things worse. It prints the service account's e-mail (which is an
identifier, not a secret, and is the thing you paste into the two consoles) and
otherwise only status codes, property names, dates and counts.

WHAT IT ANSWERS, beyond yes/no:

  * WHICH PROPERTIES the service account can see, and at what permission level.
    Read out of sites.list rather than guessed, because the siteUrl form is the
    most common way this fails — a domain property is "sc-domain:example.com"
    and a URL-prefix property is "https://example.com/", and the wrong one 403s
    without saying so.

  * THE EARLIEST DATE each property actually has data for. This decides
    something real for districtry: the site renamed on 2026-08-24, Search
    Console data belongs to a property rather than to a site, and so the
    July-August history may live in the chidistricts.com property while
    districtry.com starts at the rename. Whether the search card can span the
    report's whole window, or has to start partway through and say so, is
    exactly this number.
"""

import json
import os
import sys
import urllib.parse

import requests
from google.auth.transport.requests import Request
from google.oauth2 import service_account

GSC = "https://searchconsole.googleapis.com/webmasters/v3"
GA4 = "https://analyticsdata.googleapis.com/v1beta"
SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly",
          "https://www.googleapis.com/auth/analytics.readonly"]
# Wide enough to cover anything this project could have; the API clamps to
# whatever the property actually holds, which is the answer we want.
EARLY, TODAY = "2024-01-01", "2030-01-01"


def credentials():
    raw = os.environ.get("GOOGLE_SA_KEY", "").strip()
    if not raw:
        sys.exit("GOOGLE_SA_KEY is empty or unset — the secret did not reach "
                 "this job. Check the name in Settings > Secrets and variables "
                 "> Actions, and that the workflow passes it under `env:`.")
    try:
        info = json.loads(raw)
    except ValueError as e:
        sys.exit("GOOGLE_SA_KEY is not valid JSON (%s). Paste the WHOLE key "
                 "file, including the outer braces." % e)
    missing = [k for k in ("client_email", "private_key", "token_uri")
               if not info.get(k)]
    if missing:
        sys.exit("GOOGLE_SA_KEY is JSON but not a service-account key — "
                 "missing %s." % ", ".join(missing))
    print("service account : %s" % info["client_email"])
    print("project         : %s" % info.get("project_id", "(unset)"))
    creds = service_account.Credentials.from_service_account_info(
        info, scopes=SCOPES)
    creds.refresh(Request())          # the token itself is never printed
    print("token           : minted OK\n")
    return creds


def gsc(creds):
    h = {"Authorization": "Bearer %s" % creds.token}
    r = requests.get("%s/sites" % GSC, headers=h, timeout=60)
    print("=== Search Console ===")
    print("sites.list -> HTTP %d" % r.status_code)
    if r.status_code == 403:
        print("  403. The service account exists but is not a USER on any\n"
              "  property. Search Console permissions are separate from GCP\n"
              "  IAM: add the e-mail above under Settings > Users and\n"
              "  permissions in Search Console itself.")
        return
    if r.status_code != 200:
        print("  %s" % r.text[:300])
        return
    entries = r.json().get("siteEntry", [])
    if not entries:
        print("  Authenticated, but zero properties. Same fix as a 403: the\n"
              "  account has to be added as a user on the property.")
        return
    for e in entries:
        print("  %-40s %s" % (e.get("siteUrl"), e.get("permissionLevel")))
    print()
    for e in entries:
        earliest_and_sample(h, e.get("siteUrl"))


def earliest_and_sample(headers, site_url):
    """Earliest date with data, plus a few top queries as a live smoke check."""
    url = "%s/sites/%s/searchAnalytics/query" % (
        GSC, urllib.parse.quote(site_url, safe=""))
    print("--- %s" % site_url)

    r = requests.post(url, headers=headers, timeout=90,
                      json={"startDate": EARLY, "endDate": TODAY,
                            "dimensions": ["date"], "rowLimit": 25000})
    if r.status_code != 200:
        print("    date query -> HTTP %d  %s" % (r.status_code, r.text[:200]))
        return
    rows = r.json().get("rows", [])
    if not rows:
        print("    no data in this property at all")
        return
    days = sorted(x["keys"][0] for x in rows)
    clicks = sum(x.get("clicks", 0) for x in rows)
    impressions = sum(x.get("impressions", 0) for x in rows)
    print("    data from %s to %s  (%d days, %d clicks, %d impressions)"
          % (days[0], days[-1], len(days), clicks, impressions))

    r = requests.post(url, headers=headers, timeout=90,
                      json={"startDate": EARLY, "endDate": TODAY,
                            "dimensions": ["query"], "rowLimit": 5})
    if r.status_code == 200:
        for x in r.json().get("rows", []):
            print("      %-46s %4d clicks  %6d impr  pos %.1f"
                  % (x["keys"][0][:46], x.get("clicks", 0),
                     x.get("impressions", 0), x.get("position", 0)))
    print()


def ga4(creds):
    print("=== Google Analytics 4 ===")
    prop = os.environ.get("GA4_PROPERTY_ID", "").strip()
    if not prop:
        print("GA4_PROPERTY_ID not set, so nothing to query. It is the NUMERIC\n"
              "property id from GA4 Admin > Property Settings (e.g. 123456789)\n"
              "— not the G-XXXXXXX measurement id, which this API rejects.\n"
              "Set it as a repo secret or variable to include GA4 here.")
        return
    if not prop.isdigit():
        print("GA4_PROPERTY_ID is %r, which is not numeric. The Data API wants\n"
              "the numeric property id, not the G-XXXXXXX measurement id." % prop)
        return
    r = requests.post(
        "%s/properties/%s:runReport" % (GA4, prop),
        headers={"Authorization": "Bearer %s" % creds.token}, timeout=60,
        json={"dateRanges": [{"startDate": "28daysAgo", "endDate": "yesterday"}],
              "metrics": [{"name": "screenPageViews"}, {"name": "activeUsers"}]})
    print("runReport (property %s) -> HTTP %d" % (prop, r.status_code))
    if r.status_code == 403:
        print("  403. Add the service account e-mail above in GA4 Admin >\n"
              "  Property Access Management with the Viewer role.")
        return
    if r.status_code != 200:
        print("  %s" % r.text[:300])
        return
    rows = r.json().get("rows", [])
    if rows:
        vals = [m["value"] for m in rows[0]["metricValues"]]
        print("  last 28 days: %s page views, %s active users" % tuple(vals))
    else:
        print("  authenticated, no rows in the last 28 days")


if __name__ == "__main__":
    c = credentials()
    gsc(c)
    ga4(c)
