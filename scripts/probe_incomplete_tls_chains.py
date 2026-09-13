#!/usr/bin/env python3
"""Find county sites that are recorded as unreachable and are not — the COLES PATTERN.

WHAT IT LOOKS FOR. A server that sends only its LEAF certificate and omits the
intermediate that signed it produces a chain no plain client can complete:
requests, curl and urllib all stop at "unable to get local issuer certificate",
which in a probe log is indistinguishable from a host that does not exist. A
browser papers over it by fetching the missing issuer from the certificate's own
Authority Information Access extension, so the site loads perfectly for a person
and reads as dead to every automated sweep this project runs.

WHY IT IS A SCRIPT AND NOT A NOTE. It has now hidden three counties. Coles was
found by hand on 2026-08-17 and shipped as the 64th county. On 2026-08-21 this
sweep, run against the 27 frontier counties' clerk-mail domains, found GALLATIN —
whose gap record said the day before that the county was "DARK to this client on
every route tried" and that its Clerk's mail domain "does not resolve at all",
both false — and confirmed VERMILION, whose record said its site "is not
reachable from this project's network". Gallatin shipped the same afternoon as
the 76th county. A blocker recorded from a failed fetch is worth re-testing this
way before anybody writes to a clerk about it.

WHAT IT NEVER DOES. It does not disable verification, and neither should
anything that acts on its output. When the chain is broken it reads the leaf's
own AIA caIssuers URI, downloads that certificate, appends it to the trust store
the run already uses, and retries — reporting the intermediate's SHA-256 so a
scraper can PIN the bytes it will supply (see AIA_INTERMEDIATES in
il_county_commissioners_scraper.py and the pins in coles_county_board_scraper.py).

READING THE OUTPUT, one JSON object per host:
  * COLES-PATTERN                the find — broken chain, 200 once the AIA
                                 intermediate is supplied. `final` names where it
                                 redirected to, which is often the county's REAL
                                 site under a different domain (vercountyil.gov
                                 lands on www.vercounty.org this way).
  * ok                           answered normally; `code` may still be 403/202
  * no-dns                       independently confirmed absent, via DNS-over-
                                 HTTPS rather than the local resolver
  * unreachable                  reached the TLS layer and failed some other way
  * tls-broken-no-aia            broken chain with no issuer named — a
                                 self-signed certificate usually. NOT fixable
                                 here and not to be worked around: an
                                 unauthenticated server is a real finding.
  * tls-broken-aia-insufficient  the named issuer did not complete the chain
                                 (a hostname mismatch, or a second missing link)

RUNNING IT SOMEWHERE SANDBOXED. Behind a TLS-terminating egress proxy a denied
CONNECT arrives as a bare failure with no certificate at all, which is why DNS is
confirmed out-of-band through DNS-over-HTTPS instead of trusting the local
resolver. Do not record a county-side conclusion from a run whose proxy was
refusing the host — check `$HTTPS_PROXY/__agentproxy/status` first.

AND DO NOT MEASURE A CHAIN WITH `openssl s_client` FROM INSIDE ONE. Measured
2026-09-13 in the Claude Code sandbox: every certificate `openssl s_client`
reports is issued by `O = Anthropic, CN = Egress Gateway SDS Issuing CA
(production)` — a transparent re-signing intercept — so every host reads as
serving a complete, valid chain and a broken one is invisible. The Python stack
these scrapers use tunnels through and sees the REAL certificate: this script
returned COLES-PATTERN for www.colesco.illinois.gov and gallatinco.illinois.gov
on that same day, with their true issuers (GoDaddy and Sectigo) and intermediate
hashes, while a plain urlopen with a default context failed both on
CERTIFICATE_VERIFY_FAILED. The two vantages disagree, and the one that matches
what a scraper will do is the Python one.

Usage:
    python3 scripts/probe_incomplete_tls_chains.py HOST [HOST ...]
    python3 scripts/probe_incomplete_tls_chains.py --clerk-domains   # every county
      clerk mail domain in data/app/il-county-clerks.json, bare and www
"""

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.request

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLERKS = os.path.join(REPO_ROOT, "il", "data", "app", "il-county-clerks.json")
TIMEOUT = 25


def sh(cmd, timeout=90):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True,
                          timeout=timeout)


def roots_path():
    """Whatever store this run already trusts (certifi in CI, the proxy's bundle
    in a sandbox). Never replaced, only added to."""
    import certifi
    return (os.environ.get("REQUESTS_CA_BUNDLE")
            or os.environ.get("SSL_CERT_FILE") or certifi.where())


def dns_exists(host):
    """True/False/None — resolved out-of-band, because a proxy's refusal and a
    missing host look identical to the local resolver behind one."""
    try:
        with urllib.request.urlopen(
                "https://dns.google/resolve?name=%s&type=A" % host, timeout=20) as r:
            return bool(json.loads(r.read()).get("Answer"))
    except Exception:
        return None


def leaf_text(host):
    proxy = (os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy") or "")
    proxy = re.sub(r"^https?://", "", proxy).rstrip("/")
    opt = ("-proxy %s " % proxy) if proxy else ""
    r = sh("timeout 40 openssl s_client %s-connect %s:443 -servername %s -showcerts "
           "</dev/null" % (opt, host, host), timeout=60)
    return r.stdout + r.stderr


def probe(host, workdir):
    r = sh('curl -sSL -m %d -o /dev/null -w "%%{http_code}" https://%s/' % (TIMEOUT, host))
    code = (r.stdout or "").strip()
    if code and code != "000":
        return {"host": host, "state": "ok", "code": code}
    err = ((r.stderr or "").strip().splitlines() or [""])[0]
    if "certificate" not in err.lower():
        if dns_exists(host) is False:
            return {"host": host, "state": "no-dns"}
        return {"host": host, "state": "unreachable", "err": err[:140]}

    out = leaf_text(host)
    m = re.search(r"CA Issuers - URI:(\S+)", out)
    if not m:
        pem = re.search(r"-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----",
                        out, re.S)
        if pem:
            leaf = os.path.join(workdir, "_leaf.pem")
            open(leaf, "w").write(pem.group(0))
            m = re.search(r"CA Issuers - URI:(\S+)",
                          sh("openssl x509 -in %s -noout -text" % leaf).stdout)
    if not m:
        return {"host": host, "state": "tls-broken-no-aia", "err": err[:140]}
    aia = m.group(1)

    der = os.path.join(workdir, "_int.crt")
    pem = os.path.join(workdir, "_int.pem")
    bundle = os.path.join(workdir, "_bundle.pem")
    sh('curl -sS -m 30 -o %s "%s"' % (der, aia))
    sh("openssl x509 -inform DER -in %s -out %s || openssl x509 -in %s -out %s"
       % (der, pem, der, pem))
    sha = sh("sha256sum %s" % der).stdout.split()
    sh("cat %s %s > %s" % (roots_path(), pem, bundle))
    r2 = sh('curl -sSL -m %d --cacert %s -o /dev/null -w "%%{http_code} %%{url_effective}" '
            'https://%s/' % (TIMEOUT, bundle, host))
    parts = (r2.stdout or "").strip().split(" ", 1)
    if parts and parts[0] and parts[0] != "000":
        return {"host": host, "state": "COLES-PATTERN", "code": parts[0],
                "final": parts[1] if len(parts) > 1 else "",
                "aia": aia,
                # The DER hash, which is the form a scraper pins.
                "intermediate_sha256": sha[0] if sha else None}
    return {"host": host, "state": "tls-broken-aia-insufficient", "aia": aia,
            "err": (r2.stderr or "").strip()[:140]}


def clerk_domains():
    with open(CLERKS, encoding="utf-8") as f:
        data = json.load(f)
    hosts = []
    for county in sorted(data):
        email = ((data[county] or {}).get("email") or "").strip()
        if "@" not in email:
            continue
        dom = email.rsplit("@", 1)[1].lower()
        # The bare and www hosts are the county's WEBSITE. `gis.` is added
        # because of KNOX, 2026-08-22: its record said knoxcountyil.gov
        # "refuses every request", which is true of the website and says
        # nothing about gis.knoxcountyil.gov — a public ArcGIS Server on the
        # same domain, serving the COLES PATTERN, carrying the county's
        # townships and municipal polygons. It was found from a URL handed to
        # this project, and this sweep could not have found it: a county's
        # boundary data lives on its GIS host far more often than on its
        # www host, and that host was never probed.
        hosts += [dom, "www." + dom, "gis." + dom]
    return hosts


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("hosts", nargs="*")
    ap.add_argument("--clerk-domains", action="store_true",
                    help="probe every county clerk mail domain, bare and www")
    args = ap.parse_args()

    hosts = list(args.hosts)
    if args.clerk_domains:
        hosts += clerk_domains()
    if not hosts:
        ap.error("name at least one host, or pass --clerk-domains")

    import tempfile
    with tempfile.TemporaryDirectory() as workdir:
        found = 0
        for host in hosts:
            res = probe(host, workdir)
            if res["state"] == "COLES-PATTERN":
                found += 1
            print(json.dumps(res), flush=True)
    print("probe-incomplete-tls-chains: %d host(s), %d serving an incomplete chain"
          % (len(hosts), found), file=sys.stderr)


if __name__ == "__main__":
    main()
