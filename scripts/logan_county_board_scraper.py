#!/usr/bin/env python3
"""
Scrape Logan County's own board page into raw roster records.

Stage 1 of the two-stage pipeline (scripts/build_logan_board_roster.py is
stage 2). The county's Joomla board page lists all TWELVE members under
explicit "DISTRICT N" captions — two per district across six districts — each
with a role line (MEMBER / CHAIR / VICE CHAIR; the county elects its Chair
and Vice Chair from within the body and, unlike Woodford's directory, SAYS
who holds them), a home address (never collected), a phone and an e-mail.
This is the source whose existence overturned the original honesty-floor
blocker ("a salary publication with no district against any name") on
2026-07-31 — the gap logan-county-board-members records that history.

FETCH POSTURE: open. Plain server-rendered Joomla HTML.

The page flattens to a strict repeating rhythm per member:
    DISTRICT <n> / <ROLE> / <Name> / <home address> / <phone> / <e-mail>
The parser anchors on the DISTRICT caption and reads the block positionally,
skipping the address line by shape (it contains digits; names do not).

Usage:
    python3 logan_county_board_scraper.py [output.json]   # default: stdout
"""

import json
import re
import sys

import requests
from scraper_common import UA_ROSTER_COMPACT  # noqa: E402  (shared machinery — do not fork)
from validate_officeholder_names import is_vacancy_marker  # noqa: E402  (one reader for the word)

LIST_URL = ("https://www.logancountyil.gov/index.php?option=com_content"
            "&view=article&id=176&Itemid=541&lang=en")
UA = {"User-Agent": UA_ROSTER_COMPACT}

ROLE_MAP = {"MEMBER": None, "CHAIR": "Chair", "VICE CHAIR": "Vice Chair"}
PHONE_RE = re.compile(r"^\(?(\d{3})\)?[.\- ](\d{3})[.\- ](\d{4})$")
EMAIL_RE = re.compile(r"^([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})$")


def main():
    import html as html_mod
    r = requests.get(LIST_URL, headers=UA, timeout=60)
    r.raise_for_status()
    text = re.sub(r"<script.*?</script>|<style.*?</style>", " ", r.text, flags=re.S | re.I)
    text = html_mod.unescape(re.sub(r"<[^>]+>", "\n", text))
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    records = []
    i = 0
    while i < len(lines):
        m = re.match(r"^DISTRICT\s+(\d+)$", lines[i])
        if not m:
            i += 1
            continue
        district = int(m.group(1))
        block = lines[i + 1:i + 7]
        i += 1
        if not block or block[0].upper() not in ROLE_MAP:
            continue
        role = ROLE_MAP[block[0].upper()]
        name = block[1] if len(block) > 1 else None
        if not name or re.search(r"\d|@", name):
            continue
        if is_vacancy_marker(name):
            # THE COUNTY WRITES AN EMPTY SEAT AS A NAME, and the block is
            # otherwise a member's: "DISTRICT 5 / MEMBER / VACANT", with no
            # address, phone or e-mail after it. The word passes the name
            # filter above — it carries no digit and no "@" — so until
            # 2026-09-23 it was appended as a member called VACANT and reached
            # il/county-board/logan.html as a schema.org Person of that name.
            #
            # It is a fact about the SEAT, so it is recorded as one and the
            # builder counts it into `vacancies`, the shape this county's
            # siblings already ship and the card already renders. The role goes
            # with the record rather than being dropped: a vacancy on the Chair
            # seat is a different statement from one on a plain member's, and
            # the builder's Chair/Vice-Chair check should see it.
            records.append({"name": None, "district": district, "role": role,
                            "vacant": True, "phone": None, "email": None})
            continue
        phone = email = None
        for line in block[2:6]:
            pm = PHONE_RE.match(line)
            if pm:
                phone = "%s-%s-%s" % pm.groups()
                continue
            em = EMAIL_RE.match(line)
            if em:
                email = em.group(1).lower()
                break            # the e-mail ends the member block
        records.append({"name": name, "district": district, "role": role,
                        "phone": phone, "email": email})

    if not records:
        print("logan-board-scraper: FAIL — zero rows parsed from %s (markup change?)"
              % LIST_URL, file=sys.stderr)
        sys.exit(1)

    out = json.dumps({"source": LIST_URL, "records": records}, indent=2, ensure_ascii=False)
    if len(sys.argv) > 1:
        with open(sys.argv[1], "w", encoding="utf-8") as f:
            f.write(out)
        print("logan-board-scraper: %d records -> %s" % (len(records), sys.argv[1]))
    else:
        print(out)


if __name__ == "__main__":
    main()
