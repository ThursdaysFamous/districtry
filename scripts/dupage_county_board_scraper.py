#!/usr/bin/env python3
"""
Scrape the DuPage County Board members directory into raw roster records.

Stage 1 of the two-stage pipeline (scripts/build_dupage_county_board_roster.py
is stage 2), mirroring the Will County board scraper. Unlike Will's, DuPage's
directory (dupagecounty.gov, a Revize CMS "business directory") is plain
server-rendered HTML with no JS challenge, so requests + BeautifulSoup suffice.

Each member is a <div class="rz-business-block"> carrying an <h2> name, an
inline "District N" field, term dates, a member-specific tel: phone and mailto:
email, and a "More about <name>" link to the member's detail page. Everything
the card needs is on this one list page, so a single fetch suffices. The Board
Chair is elected countywide (no district) and is emitted with district=null,
role="Chair".

Names, phones, and emails are read verbatim from the county's own directory —
never guessed. The per-member tel: link is the member's own published number
(distinct from the general 630-407-6500 board-office line).

E-MAIL ON ANY DOMAIN, SINCE 2026-10-17. Until that day only a mailto: on the
county's own domain was read. Under Adam's choice that day to publish personal
e-mail addresses ("E-mails too"), the address a member's own block links ships
whatever its domain, checked for its shape (scraper_common.person_email_problem).
Site-template and role inboxes (BOILERPLATE_EMAIL) are still never a member's;
an address linked from two or more member blocks is an office's or a shared
inbox and ships on neither; and an address scripts/undeliverable.py lists ships
nowhere. Measured 2026-10-17 on the list page: each of the 19 blocks links
exactly one mailto:, every one on the county's domain, and the page links no
mailto: outside the blocks.

Usage:
    python3 dupage_county_board_scraper.py [output.json]   # default: stdout
"""

import json
import re
import sys

import requests
from bs4 import BeautifulSoup
import undeliverable  # noqa: E402  (the fleet's withhold list)
from scraper_common import require_robots_once, UA_ROSTER_COMPACT, fetch as fetch_with_retry, person_email_problem  # noqa: E402  (shared machinery — do not fork)

BASE = "https://www.dupagecounty.gov"
LIST_URL = BASE + "/government/county_board/county_board_members/"
UA = {"User-Agent": UA_ROSTER_COMPACT}
# mailto: local-parts that are site chrome / role inboxes, not a member address.
BOILERPLATE_EMAIL = ("noreply", "webpageupdate", "bootstrap", "webmaster", "info@")
# Not an allow-list since 2026-10-17: it only decides which address a block
# keeps when it links more than one, so that a member carries one address.
COUNTY_EMAIL_DOMAIN = "dupagecounty.gov"


def fetch(url):
    # scraper_common.fetch retries 429/5xx (numeric Retry-After honoured,
    # capped) and refuses to retry 401/403/404 — the Henry rule. Parsing and
    # every page check stay in this file.
    require_robots_once(url, UA["User-Agent"], headers=UA,
                        label="il-dupage-county-board-scraper")
    return fetch_with_retry(url, UA, timeout=60).text


def abs_url(href):
    href = (href or "").strip()
    if not href:
        return None
    if href.startswith("http"):
        return href
    return BASE + "/" + href.lstrip("/")


def format_phone(raw):
    """Normalize a tel: value to XXX-XXX-XXXX; leave anything unexpected as-is."""
    d = re.sub(r"\D", "", raw or "")
    if len(d) == 11 and d[0] == "1":
        d = d[1:]
    if len(d) == 10:
        return "%s-%s-%s" % (d[:3], d[3:6], d[6:])
    return (raw or "").strip() or None


def block_email(block):
    """The member's address from a mailto: link in their own block, if any.

    Any domain (see the module docstring). Where the block links two or more
    addresses, the one on the county's domain is kept and the others are not
    read, so the member carries one address; with none on the county's domain,
    the first the block links is kept."""
    found = []
    for a in block.find_all("a", href=True):
        h = a["href"].strip()
        if h.lower().startswith("mailto:"):
            addr = h[7:].split("?")[0].strip()
            if (addr and not addr.lower().startswith(BOILERPLATE_EMAIL)
                    and addr.lower() not in {f.lower() for f in found}):
                found.append(addr)
    for addr in found:
        if addr.lower().endswith("@" + COUNTY_EMAIL_DOMAIN):
            return addr
    return found[0] if found else None


def seat_label(rec, records):
    """'DuPage County District 3, member 2 of 3 in page order', or the Chair.
    Names the seat for an error or a note, never the address."""
    if rec["role"] == "Chair":
        return "DuPage County Board Chair"
    same = [r for r in records if r["district"] == rec["district"] and r["role"] != "Chair"]
    place = next(i for i, r in enumerate(same, 1) if r is rec)
    return ("DuPage County District %s, member %d of %d in page order"
            % (rec["district"], place, len(same)))


def check_emails(records):
    """Shape-check every address and withhold the ones that are not a member's
    own: an address linked from two or more member blocks, and one
    scripts/undeliverable.py lists. Prints the seat, never the address."""
    linked = {}
    for rec in records:
        if rec.get("email"):
            linked[rec["email"].lower()] = linked.get(rec["email"].lower(), 0) + 1
    for rec in records:
        email = rec.get("email")
        if not email:
            continue
        seat = seat_label(rec, records)
        problem = person_email_problem(email)
        if problem:
            sys.exit("dupage-board-scraper: FAIL — %s: the directory's e-mail %s"
                     % (seat, problem))
        if email.lower() in undeliverable.UNDELIVERABLE:
            why = "scripts/undeliverable.py lists it as an address that cannot receive mail"
        elif linked[email.lower()] > 1:
            why = ("it is linked from %d member blocks, so it is not this "
                   "member's own" % linked[email.lower()])
        else:
            continue
        del rec["email"]
        print("  WITHHELD the e-mail the directory links for %s: %s" % (seat, why),
              file=sys.stderr)


def block_phone(block):
    """The member's own published number from the block's tel: link."""
    for a in block.find_all("a", href=True):
        h = a["href"].strip()
        if h.lower().startswith("tel:"):
            return format_phone(h[4:])
    return None


def scrape():
    soup = BeautifulSoup(fetch(LIST_URL), "html.parser")
    blocks = soup.find_all("div", class_="rz-business-block")
    records = []
    for b in blocks:
        h2 = b.find("h2")
        if not h2:
            continue
        raw_name = h2.get_text(" ", strip=True)
        is_chair = bool(re.search(r"chair", raw_name, re.I))
        name = re.sub(r"\s*[–—-]\s*chair\s*$", "", raw_name, flags=re.I).strip()
        if not name:
            continue
        text = b.get_text(" ", strip=True)
        dm = re.search(r"District\s+([1-6])\b", text)
        district = int(dm.group(1)) if (dm and not is_chair) else None
        link = b.find("a", href=re.compile(r"/[A-Za-z]+\.php", re.I))
        rec = {"name": name, "district": district,
               "role": "Chair" if is_chair else "Member",
               "url": abs_url(link["href"]) if link else None}
        phone = block_phone(b)
        email = block_email(b)
        if phone:
            rec["phone"] = phone
        if email:
            rec["email"] = email
        records.append(rec)
    check_emails(records)
    return records


def main():
    records = scrape()
    n_dist = sum(1 for r in records if r["district"] is not None)
    n_chair = sum(1 for r in records if r["role"] == "Chair")
    n_email = sum(1 for r in records if r.get("email"))
    n_phone = sum(1 for r in records if r.get("phone"))
    print("scraped %d records (%d district members, %d chair, %d phones, %d emails)"
          % (len(records), n_dist, n_chair, n_phone, n_email), file=sys.stderr)
    out = json.dumps(records, ensure_ascii=False, indent=2) + "\n"
    if len(sys.argv) >= 2:
        with open(sys.argv[1], "w") as f:
            f.write(out)
        print("wrote %s" % sys.argv[1], file=sys.stderr)
    else:
        sys.stdout.write(out)


if __name__ == "__main__":
    main()
