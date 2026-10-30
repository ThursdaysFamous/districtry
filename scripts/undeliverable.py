"""Addresses this repo publishes nowhere, because mail to them cannot arrive.

WHY THIS IS SHARED RATHER THAN PER-BUILDER. build_county_clerk_roster.py has
carried a KNOWN_UNDELIVERABLE list since 2026-07-31, when a letter to White
County's published clerk address hard-bounced after five days — the card had
been telling a reader "write to your clerk here" while nothing they sent could
arrive. That is the honesty rule failing quietly, and it turned out not to be
one county's problem: an MX sweep of every shipped address on 2026-09-04 (3,336
addresses, 768 domains, 0 network skips, every finding confirmed on a second
independent resolver) found nineteen more across three instances.

WHAT A FINDING HERE IS, EXACTLY. The domain does not resolve at all — no MX, no
A, no AAAA, NXDOMAIN. That is the only DNS evidence strong enough to withhold
on. A domain that resolves but publishes no MX has an IMPLICIT MX at its A
record (RFC 5321 §5.1) and is NOT here; validate_card_links.py reports those
separately as unverified, because only sending settles them.

A .gov NAME DOES NOT SHOW NXDOMAIN (measured 2026-10-17). The .gov zone answers
a name that does not exist with NOERROR and no records: a made-up .gov name
answers that way on Google's and Cloudflare's resolvers, and so does
washingtonco.illnois.gov, recorded below as NXDOMAIN on 2026-09-04, while a
made-up .com name answers NXDOMAIN. So for a .gov domain the finding is that it
answers exactly as a made-up .gov name does: no NS delegation, no MX, no A and
no AAAA record.

THE CORRECTION IS NEVER APPLIED. Every one of these is one character from a
domain that does resolve — warrecountyil.gov/warrencountyil.gov,
yahoo.ocm/yahoo.com — and the obvious fix was measured live for all of them.
That is evidence for the DIAGNOSIS and nothing more. Douglas County settled
this in Illinois: its yearbook printed `douglascountuil.gov` and the builder
dropped the address rather than "silently correcting a character in someone's
contact detail" — by a county-domain check until 2026-10-17, and through this
list since, when Adam's choice that day to publish personal e-mail addresses
("E-mails too") retired the domain check. Officeholder data is never guessed,
and a contact detail is officeholder data.

WHAT STILL SHIPS. Only the address is withheld. The name, office, phone, party
and page URL are untouched, so every contact route that works survives and the
card simply stops offering one that does not. No app change is needed — each
card renders its e-mail row only when the field is present.

WHAT DOES NOT BELONG HERE: A CORRECT ADDRESS WHOSE ROUTE IS BROKEN. Every
entry below is a MISTYPED ADDRESS, and that is what makes the list safe — the
moment a source publishes the right one the entry stops matching and says so.
A correct address on a domain whose MX host does not resolve is a different
thing: the county can fix its DNS tomorrow without the address changing by a
character, so an entry here would never retire and would go on withholding a
working contact. Those are REPORTED by validate_card_links.py and left to the
monthly issue — `auditor@harrisoncountyia.org` is one today (its MX names
mail.harrisoncountyia.org, which is NXDOMAIN on both resolvers).

RETIRING AN ENTRY, AND WHY THE AUDIT IS A GATE RATHER THAN A PRINTED LINE.
The first version of this module printed a RETIRE line from the builders and
returned a list every caller discarded, so an entry that had outlived its
reason was a permanent silent hole — the exact state check_roster_retention.py
records having had to fix in ACCEPTED_DROPS. Worse, it could not have been
trusted anyway: the "addresses seen" set was process-global, so a builder that
skipped a county on a count guard printed a RETIRE for that county's entry
having simply never looked at it.

So the audit is `--check`, it reads the SHIPPED TREE rather than one run's
memory, and it FAILS:

  * an entry naming a data/app file that no instance has  -> orphaned
  * an entry whose address is in the shipped tree anyway  -> the withhold
    stopped firing, which is the failure this list exists to prevent

The third test needs DNS and lives in validate_card_links.py's monthly mail
section: a listed domain that has come BACK — resolving, with a live mail
route — is reported so the entry can be retired. That is the same inversion
EXPECTED_UNREACHABLE already uses, where becoming reachable is the finding.

If an address is ever reported working rather than re-addressed, verify by
SENDING — never by assuming, which is the limit the White County bounce
recorded from the other direction: its DNS was healthy the whole time.
"""

# address (lower-case) -> (scope, the measurement that justifies withholding it)
#
# SCOPE IS THE data/app FILE THE ADDRESS SHIPS IN, and it is what makes the
# RETIRE audit honest: a builder that re-audited the whole list would report
# twelve other instances' entries as stale on every run, which is noise that
# teaches a reader to ignore the line. Each builder audits its own file.
UNDELIVERABLE = {
    # ---- Illinois: municipal-officials.json, carried from county clerk
    #      directories exactly as each clerk published them.
    "lwilson@cityofalton.il.gov": (
        "municipal-officials.json",
        "cityofalton.il.gov is NXDOMAIN (measured 2026-09-04, Google and "
        "Cloudflare DoH). The city is at cityofaltonil.gov."),
    "jsisti@villageofgrandvew.gov": (
        "municipal-officials.json",
        "villageofgrandvew.gov is NXDOMAIN (2026-09-04) — 'grandvew' for "
        "'grandview'. The village's own domain resolves and carries MX."),
    "grandview@villaegofgrandview.gov": (
        "municipal-officials.json",
        "villaegofgrandview.gov is NXDOMAIN (2026-09-04) — 'villaeg' for "
        "'village'. A SECOND typo of the same village's domain, published "
        "beside the first, which is why this list is keyed by address."),
    "eeeten@gmail.org": (
        "municipal-officials.json",
        "gmail.org is NXDOMAIN (2026-09-04) — almost certainly gmail.com, and "
        "a personal mailbox is exactly where a guessed correction would do the "
        "most harm."),
    "etajenhorst@hormil.xom": (
        "municipal-officials.json",
        "hormIL.XOM is NXDOMAIN (2026-09-04) — '.xom' is not a TLD."),
    "trusteechristofilakos@vilageofjerome.com": (
        "municipal-officials.json",
        "vilageofjerome.com is NXDOMAIN (2026-09-04) — 'vilage' for 'village'."),
    "mmcdonald@offallon.org": (
        "municipal-officials.json",
        "offallon.org is NXDOMAIN (2026-09-04). O'Fallon publishes on a "
        "different domain; this one has no DNS record of any kind."),
    "brichbark@southerview.us": (
        "municipal-officials.json",
        "southerview.us is NXDOMAIN (2026-09-04) — the village is Southern "
        "View."),
    "sstillwell@sugargroveil.org": (
        "municipal-officials.json",
        "sugargroveil.org is NXDOMAIN (2026-09-04)."),

    # ---- Illinois: county board rosters, scraped from each county's own page.
    "twinkler@warrecountyil.gov": (
        "warren-county-board-members.json",
        "warrecountyil.gov is NXDOMAIN (2026-09-04) — a dropped 'n'. The "
        "county's real domain resolves and carries MX, so this is the county's "
        "own typo on its own page."),
    "doug.bening@washingtonco.illnois.gov": (
        "washington-county-board-members.json",
        "washingtonco.illnois.gov is NXDOMAIN (2026-09-04) — 'illnois' for "
        "'illinois'."),
    "travis.wilson@douglascountuil.gov": (
        "douglas-county-board-members.json",
        "douglascountuil.gov answers exactly as a made-up .gov name does: "
        "no NS delegation, no MX, no A and no AAAA record, on Google's and "
        "Cloudflare's resolvers (measured 2026-10-17; a .gov name cannot "
        "show NXDOMAIN, see the docstring). It is a typo for "
        "douglascountyil.gov, the domain of the county's other six "
        "members' addresses; the yearbook prints it beside District 1. The "
        "Douglas builder dropped it by a county-domain test until "
        "2026-10-17 and drops it through this list since."),

    # ---- Iowa: ia-county-officers.json.
    "fpowless@monroecounty.iowa": (
        "ia-county-officers.json",
        "monroecounty.iowa is NXDOMAIN (2026-09-04) — the domain is "
        "monroecounty.iowa.gov, which Monroe's recorder and sheriff both use. "
        "STALE RATHER THAN MISREAD: run against the source today "
        "(iowatreasurers.org, county 68) the scraper produces the complete "
        "address, classified 'witnessed'. So this entry exists to stop a dead "
        "address shipping until the next weekly rebuild, and it retires itself "
        "the moment that rebuild writes the full domain."),

    # ---- Wisconsin: county-board-members.json. Both are PERSONAL mailboxes a
    #      county publishes as the way to reach that supervisor, which is
    #      normal there (Florence publishes six of eleven on consumer domains)
    #      — so neither is a county-domain problem, just a mistyped address.
    "jeromekremp@yahoo.ocm": (
        "county-board-members.json",
        "yahoo.ocm is NXDOMAIN (2026-09-04) — '.ocm' is not a TLD. Clark "
        "County, District 25."),
    "jmills@florwi.org": (
        "county-board-members.json",
        "florwi.org is NXDOMAIN (2026-09-04): no SOA, NS, A or MX. Florence "
        "County. Recorded on 2026-09-03 as an address that 'routes mail fine' "
        "— that claim was never measured and was wrong."),

    # ---- West Virginia: wv-county-officials.json, from the Secretary of
    #      State's 2025 directory of county officials, which prints each
    #      address in the official's own entry. Measured 2026-10-29 on
    #      Google's and Cloudflare's DoH resolvers; a made-up .gov name
    #      (madeupname12345.gov) answered the same way as the two .gov
    #      entries below, the docstring's test for a .gov name.
    "lancewheeler@kanwha.us": (
        "wv-county-officials.json",
        "kanwha.us is NXDOMAIN (2026-10-29) — 'kanwha' for 'kanawha'. Kanawha "
        "County, Commissioner; the other two commissioners' addresses are on "
        "kanawha.us, which resolves and carries MX."),
    "sallierobinson@kanwha.us": (
        "wv-county-officials.json",
        "kanwha.us is NXDOMAIN (2026-10-29). Kanawha County, Assessor."),
    "info@kanwha.us": (
        "wv-county-officials.json",
        "kanwha.us is NXDOMAIN (2026-10-29). Kanawha County, Surveyor."),
    "drusnak@kanawhaprocecutor.us": (
        "wv-county-officials.json",
        "kanawhaprocecutor.us is NXDOMAIN (2026-10-29) — 'procecutor' for "
        "'prosecutor'. Kanawha County, Prosecuting Attorney."),
    "susan.lemon@courts.wv.gov": (
        "wv-county-officials.json",
        "courts.wv.gov is NXDOMAIN (2026-10-29); the state's court system "
        "is at courtswv.gov. Braxton County, Circuit Clerk."),
    "william.stevens@courts.wv": (
        "wv-county-officials.json",
        "courts.wv is NXDOMAIN (2026-10-29) — '.wv' is not a TLD. Lincoln "
        "County, Circuit Clerk."),
    "lonnie.hannah@courtyswv.gov": (
        "wv-county-officials.json",
        "courtyswv.gov answers exactly as a made-up .gov name does: no NS "
        "delegation, no MX, no A and no AAAA record (2026-10-29) — 'courtys' "
        "for 'courts'. Mingo County, Circuit Clerk."),
    "jess.mcmullen@fayettecountwv.gov": (
        "wv-county-officials.json",
        "fayettecountwv.gov answers exactly as a made-up .gov name does "
        "(2026-10-29) — 'countwv' for 'countywv'; fayettecountywv.gov "
        "resolves and carries MX. Fayette County, Sheriff."),
}


def withhold(email, where=""):
    """(address_to_ship, note) — the address, or None when it cannot receive.

    `where` is printed with any drop so a weekly run says which record lost an
    address rather than only that one did.
    """
    if not email:
        return email, None
    entry = UNDELIVERABLE.get(email.strip().lower())
    if entry is None:
        return email, None
    _scope, reason = entry
    import sys
    print("undeliverable: dropped %s%s — %s"
          % (email, (" from %s" % where) if where else "", reason),
          file=sys.stderr)
    return None, reason


def audit(repo_root=None):
    """[problem, ...] — every way this list can have gone stale, from the tree.

    Static: no network, no run memory. See the module docstring for why the
    audit reads the shipped files rather than what a builder happened to see.
    """
    import glob
    import json
    import os

    repo_root = repo_root or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    shipped = {}                      # basename -> [paths]
    for path in glob.glob(os.path.join(repo_root, "*", "data", "app", "*.json")):
        shipped.setdefault(os.path.basename(path), []).append(path)

    problems = []
    scopes = sorted({sc for sc, _r in UNDELIVERABLE.values()})
    for scope in scopes:
        if scope not in shipped:
            problems.append(
                "%s is named by an entry but no instance ships a file with that "
                "name — the entry is orphaned; delete it or fix its scope" % scope)

    # An address that is still in the tree means the withhold did not fire for
    # it: the builder stopped calling withhold(), or writes the field by a
    # route the sweep misses. Either way the card is rendering a dead address.
    wanted = {a: sc for a, (sc, _r) in UNDELIVERABLE.items()}
    for scope, paths in shipped.items():
        if scope not in scopes:
            continue
        for path in paths:
            blob = open(path, encoding="utf-8").read().lower()
            for addr, sc in wanted.items():
                if sc == scope and addr in blob:
                    problems.append(
                        "%s still contains %s, which this list says is "
                        "undeliverable — the withhold is not firing for it"
                        % (os.path.relpath(path, repo_root), addr))
    return problems


def main():
    import sys
    problems = audit()
    if problems:
        print("undeliverable: FAIL", file=sys.stderr)
        for p in problems:
            print("  - %s" % p, file=sys.stderr)
        sys.exit(1)
    print("undeliverable: OK — %d withheld address(es) across %d shipped file(s), "
          "none orphaned and none still in the tree"
          % (len(UNDELIVERABLE), len({sc for sc, _r in UNDELIVERABLE.values()})))


if __name__ == "__main__":
    main()
