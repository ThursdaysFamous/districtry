#!/usr/bin/env python3
"""A verification bundle for the servers that omit their intermediate — the COLES PATTERN.

WHAT THE PATTERN IS. A server that sends only its LEAF certificate and leaves
out the intermediate that signed it produces a chain no plain client can
complete: requests, curl and urllib all stop at "unable to get local issuer
certificate". A browser papers over it by fetching the missing issuer from the
certificate's own Authority Information Access extension, so the site loads
perfectly for a person and reads as DEAD to every automated sweep. That single
misreading has cost this project four counties: Coles (found 2026-08-17, shipped
as the 64th), Vermilion and Gallatin (2026-08-21, Gallatin shipped the same
afternoon as the 76th), and Knox's GIS server (2026-08-22), whose record said
the county "refuses every request" when what refused was its website.

WHY THIS IS SHARED CODE. A pinned hash that exists in two files is a pin that
drifts; this is the one copy. An earlier version of this docstring said every
affected host sat behind the SAME GoDaddy intermediate — that stopped being
true the day Gallatin (Sectigo) and Vermilion (GoGetSSL) were chased, and for
a while each of those scrapers carried its own inline copy of this machinery.
The 2026-08-24 scripts audit folded all of them back here, where the table
below now keys three CAs.

WHAT IT NEVER DOES. It does not disable verification and nothing built on it
may. The download is over plain HTTP BY DESIGN — that is the AIA URI the
certificate itself publishes — and is safe because the bytes are pinned by hash
here and because the caller's requests still verify the whole chain against
the trusted roots plus this one extra anchor. If a county fixes its chain this
keeps working (a spare trust anchor is harmless). If a county moves to a
different CA the pin fails LOUDLY, which is the state a human can act on.

NOT GATED ON robots.txt, AND THE REASON IS THE HANDSHAKE RATHER THAN THE HOST.
What this fetches is a CERTIFICATE -- an intermediate CA certificate from the
AIA url printed inside a leaf certificate a host just served us, at
certificates.godaddy.com, crt.sectigo.com and crt.usertrust.com. It is a step
in completing a TLS chain, over plain http because a certificate is signed and
carries its own integrity, and each one is pinned by hash here. No page is
read, no link is followed, no url is discovered; the address comes out of the
certificate the host itself handed over in order to be verified.

THE TEST IS WHETHER SOMEBODY'S PAGES ARE BEING READ, never which host answers.
robots.txt governs a crawler reading a site's public content, and a CA's
certificate repository is infrastructure a TLS client is expected to fetch --
the whole point of an AIA url is that clients follow it. Gating it would also
be circular in the case this module exists for: the four hosts it completes
chains for serve an incomplete chain, so THEIR robots.txt cannot be read until
the intermediate is in hand. An unauthenticated read of an ordinary page on
any of these three hosts would be gated in full.
"""

import base64
import hashlib
import os
import tempfile
import urllib.request

# The AIA caIssuers URIs printed inside these counties' own leaf certificates,
# and the SHA-256 of the certificate each serves. Pinned so the download cannot
# be substituted. Keys are the intermediate's identity, not a county's: two
# counties behind the same CA share an entry, and a county that re-keys its
# chain gets a deliberate pin update here, never a loosened check.
INTERMEDIATES = {
    "godaddy-g2": {  # colesco.illinois.gov, gis.knoxcountyil.gov
        "url": "http://certificates.godaddy.com/repository/gdig2.crt",
        "sha256": "973a41276ffd01e027a2aad49e34c37846d3e976ff6a620b6712e33832041aa6",
        "subject_cn": "Go Daddy Secure Certificate Authority - G2",
    },
    "sectigo-ov-r40": {  # gallatinco.illinois.gov
        "url": "http://crt.sectigo.com/SectigoPublicServerAuthenticationCAOVR40.crt",
        "sha256": "8eb2f17d668941c39a7fca0cee127ae0ebaf444610631cca3cd19eab46c5824a",
        "subject_cn": "Sectigo Public Server Authentication CA OV R40",
    },
    "gogetssl-rsa-dv": {  # www.vercounty.org
        "url": "http://crt.usertrust.com/GoGetSSLRSADVCA.crt",
        "sha256": "43cac31ef8e8ba1b4b16b8206e4c0a26c5badb2fc3aa09e90170e41b66c2fd64",
        "subject_cn": "GoGetSSL RSA DV CA",
    },
}

TIMEOUT = 60


def ca_bundle(label, key="godaddy-g2"):
    """The trusted roots + the intermediate these servers omit.

    Returns the path to a temp file the caller is responsible for deleting.

    `label` names the caller in the failure message, because the thing a human
    needs to know first is WHICH county's certificate authority moved. `key`
    picks the pinned intermediate from INTERMEDIATES above.

    The roots are whatever store the rest of the run already trusts: in CI no
    override is set and that is certifi (requests' own store, so callers trust
    exactly what every other scraper in this repo trusts); behind a
    TLS-terminating egress proxy REQUESTS_CA_BUNDLE/SSL_CERT_FILE names a
    bundle that includes that proxy's root, and swapping certifi in for it
    would break the one fetch this function exists to enable.
    """
    import certifi

    spec = INTERMEDIATES[key]
    roots_path = (os.environ.get("REQUESTS_CA_BUNDLE")
                  or os.environ.get("SSL_CERT_FILE") or certifi.where())

    der = urllib.request.urlopen(spec["url"], timeout=TIMEOUT).read()
    got = hashlib.sha256(der).hexdigest()
    if got != spec["sha256"]:
        raise SystemExit(
            "%s: the intermediate at %s hashed %s, expected %s — the certificate\n"
            "authority may have changed. Do NOT loosen this check; re-read the\n"
            "leaf's AIA extension and update the pin deliberately."
            % (label, spec["url"], got, spec["sha256"]))
    body = base64.encodebytes(der).decode("ascii")
    pem = "-----BEGIN CERTIFICATE-----\n%s-----END CERTIFICATE-----\n" % body
    bundle = tempfile.NamedTemporaryFile(suffix=".pem", mode="w", delete=False)
    with open(roots_path, "r") as roots:
        bundle.write(roots.read())
    bundle.write("\n# %s (AIA-supplied; the server omits it)\n"
                 % spec["subject_cn"])
    bundle.write(pem)
    bundle.close()
    return bundle.name
