#!/usr/bin/env python3
"""
Build wv/data/app/wv-city-councils.json: the council members of the West
Virginia cities whose wards the City Council Ward layer draws
(wv/data/app/wv-city-wards.json, built by build_wv_city_wards.py), read from
each city's own council page, so the ward card can name who represents a
point without reaching a third-party host at click time.

WHICH CITIES. Only the ones whose wards are drawn, keyed by the Census place
id the ward file carries: today Charleston alone. Huntington, Parkersburg and
Wheeling were asked for their ward maps on 2026-10-21 (docs/ASK_DRAFTS.md);
each joins CITIES in the change that draws its wards.

THE SOURCE, MEASURED 2026-11-02. Charleston's City Council page
(www.charlestonwv.gov/government/city-council) is one table with a row for
each of the council's 26 seats: 20 members elected by ward and 6 at large.
Each row gives the member's name under a photograph, the seat ("Ward 1
Council Member", "Council Member At-Large") linked to a page of the member's
own, a block of contact lines, and an e-mail address. On 2026-11-02 the Ward
16 row named no one (a dash where the name goes), and no telephone or e-mail
address was printed in two members' rows or was City Hall's own.

WHAT SHIPS, AND WHAT NEVER DOES. For each seat: the seat, the name, every
telephone printed in that member's own row with the label the page gives it
("H:" home, "C:" cell, "O:" office), the member's e-mail address and the link
to the member's page. The fleet's rule since 2026-10-17 is that an official's
own telephone and e-mail address ship wherever a government source prints them
beside that official, whatever kind of number or address it is; one printed
beside two or more members, or equal to City Hall's line, is the council's and
rides nobody's row. THE CONTACT
BLOCK ALSO PRINTS A STREET ADDRESS FOR EVERY MEMBER, most of them homes, and
NO STREET ADDRESS IS EVER WRITTEN TO THE FILE: the parser keeps only the
telephone numbers it finds in the block and drops every other line, and
--check refuses a file holding anything that looks like a street address. The
council's own office is City Hall, from the page's Contact Us block.

A SEAT THE PAGE NAMES NO ONE FOR IS NOT CALLED VACANT, because the page does
not say so: it ships as `name: null` and the card says the city's page names no
one for it.

THE ELECTION. Charleston elects its mayor and all 26 council members on
3 November 2026. This job reads the page every week, so the names change when
the city changes its page, in a reviewed pull request.

ROBOTS. www.charlestonwv.gov's robots.txt (2,027 bytes, Drupal's default, read
2026-11-02 with this script's own User-Agent) disallows nothing this script
reads and states no delay. A run is one request.

Honesty: names are never guessed and nothing is carried over from an earlier
run. A page that does not have the expected shape stops the build.

Usage:
    python3 wv/scripts/build_wv_city_councils.py [output_dir]
    python3 wv/scripts/build_wv_city_councils.py --offline DIR [output_dir]
    python3 wv/scripts/build_wv_city_councils.py --save DIR [output_dir]
    python3 wv/scripts/build_wv_city_councils.py --check

--check reads the SHIPPED file and nothing else, offline: one record for each
city in CITIES, every ward seat once, the at-large count, no street address
and no telephone holding more than one number. It proves the file is what a
build writes; it never proves the page has not moved since.

--save writes the page fetched into DIR; --offline reads it back instead of
fetching.
"""

import datetime
import html as html_module
import json
import os
import re
import sys
import time
import urllib.request

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(_HERE)), "scripts"))
from scraper_common import require_robots_once  # noqa: E402  (FLEET_SHARED)
from undeliverable import withhold  # noqa: E402  (FLEET_SHARED)

USER_AGENT = "districtry/1.0 (+https://districtry.com/wv/)"
HEADERS = {"User-Agent": USER_AGENT}
ATTEMPTS = 3
RETRY_SECONDS = 5.0

INSTANCE_ROOT = os.path.dirname(_HERE)
DEFAULT_OUT_DIR = os.path.join(INSTANCE_ROOT, "data", "app")
OUT_NAME = "wv-city-councils.json"

# One entry per city whose wards are drawn. `wards` and `at_large` are the
# council's seats as the city's charter fixes them, so a page listing more or
# fewer stops the build; `max_unnamed` is how many seats the page may leave
# without a name before the build treats the page as broken rather than as
# vacancies.
CITIES = [
    {
        "geoid": "5414600",
        "city": "Charleston",
        "body": "Charleston City Council",
        "page": "https://www.charlestonwv.gov/government/city-council",
        "wards": 20,
        "at_large": 6,
        "max_unnamed": 3,
    },
]

ROW_RE = re.compile(r'<tr class="councilRow">(.*?)</tr>', re.S)
CELL_RE = re.compile(r'<td[^>]*class="views-field ([^"]*)"[^>]*>(.*?)</td>', re.S)
CELLS = {"image": "field-council-image", "seat": "views-field-title",
         "contact": "field-council-member-contact-inf", "email": "field-council-email"}
SEAT_RE = re.compile(r'<a href="([^"]+)"[^>]*>\s*(.*?)\s*</a>', re.S)
WARD_SEAT_RE = re.compile(r"^Ward (\d+) Council Member$")
AT_LARGE_SEAT = "Council Member At-Large"
# A telephone in a contact block, with the label the page puts before it. The
# page breaks some numbers across lines ("O: (304)" / "414-6019"), so the block
# is read with its lines joined.
PHONE_RE = re.compile(
    r"(?:\b(H|C|O|Phone)\s*:\s*-?\s*)?(?<!\d)\(?\s*(\d{3})\s*\)?\s*[-.\s]?\s*(\d{3})"
    r"\s*[-.]\s*(\d{4})(?!\d)")
PHONE_LABELS = {"H": "Home", "C": "Cell", "O": "Office", "Phone": None, "": None}
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+'-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}$")
MAILTO_RE = re.compile(r'href="mailto:([^"]+)"')
# The page's Contact Us block, the council's own office.
CITY_HALL_RE = re.compile(
    r"Contact Us\s*City Hall\s*(\d+ Virginia St\.? East)\s*(Charleston, WV \d{5})\s*"
    r"(\d{3})\.(\d{3})\.(\d{4})")
# What --check refuses: a house number and a street word, in any value.
STREET_RE = re.compile(
    r"\b\d+\s+(?:[A-Z][A-Za-z.]*\s+){0,4}(?:St|Street|Ave|Avenue|Rd|Road|Dr|Drive|Ln|Lane|"
    r"Ct|Court|Blvd|Way|Pl|Place|Cir|Circle|Pike|Hwy|Highway|Ter|Terrace)\b\.?", re.I)


def fail(msg):
    raise SystemExit("build-wv-city-councils: FATAL: %s" % msg)


def fetch(url):
    require_robots_once(url, USER_AGENT, headers=HEADERS, label="wv-city-councils")
    last = None
    for attempt in range(ATTEMPTS):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=60) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(RETRY_SECONDS * (attempt + 1))
    raise RuntimeError("could not read %s: %s" % (url, last))


def page_file(url):
    return re.sub(r"[^A-Za-z0-9._-]+", "_", url.split("://", 1)[-1]) + ".html"


def get_page(url, offline=None, save=None):
    if offline:
        with open(os.path.join(offline, page_file(url)), encoding="utf-8") as fh:
            return fh.read()
    body = fetch(url)
    if save:
        os.makedirs(save, exist_ok=True)
        with open(os.path.join(save, page_file(url)), "w", encoding="utf-8") as fh:
            fh.write(body)
    return body


def text_of(fragment):
    fragment = re.sub(r"<br\s*/?>|</p>", "\n", fragment)
    fragment = re.sub(r"<[^>]+>", "", fragment)
    return html_module.unescape(fragment).replace("\xa0", " ")


def phones_of(block):
    """[{number, label?}] for every telephone in a contact block, in order;
    every other line of the block (the street address) is dropped here."""
    flat = re.sub(r"\s+", " ", text_of(block))
    out = []
    for label, a, b, c in PHONE_RE.findall(flat):
        entry = {"number": "(%s) %s-%s" % (a, b, c)}
        if PHONE_LABELS.get(label):
            entry["label"] = PHONE_LABELS[label]
        if entry["number"] not in [p["number"] for p in out]:
            out.append(entry)
    return out


def parse_council(body, c):
    rows = ROW_RE.findall(body)
    if len(rows) != c["wards"] + c["at_large"]:
        fail("%s: the council page has %d member rows, not %d"
             % (c["city"], len(rows), c["wards"] + c["at_large"]))
    wards, at_large = {}, []
    for row in rows:
        cells = {}
        for cls, value in CELL_RE.findall(row):
            for key, marker in CELLS.items():
                if marker in cls:
                    cells[key] = value
        if set(cells) != set(CELLS):
            fail("%s: a council row lacks %s" % (c["city"], sorted(set(CELLS) - set(cells))))
        name = text_of(re.split(r"<br\s*/?>", cells["image"])[-1]).strip()
        if not re.search(r"[A-Za-z]", name):
            name = None
        seat_m = SEAT_RE.search(cells["seat"])
        if not seat_m:
            fail("%s: a council row has no seat link" % c["city"])
        href, seat_text = seat_m.group(1), re.sub(r"\s+", " ", text_of(seat_m.group(2))).strip()
        url = href if href.startswith("http") else "https://www.charlestonwv.gov" + href
        rec = {"name": name}
        if name:
            phones = phones_of(cells["contact"])
            if phones:
                rec["phones"] = phones
            emails = MAILTO_RE.findall(cells["email"])
            if len(set(e.lower() for e in emails)) > 1:
                fail("%s %s: two e-mail addresses in one row" % (c["city"], seat_text))
            if emails:
                email, _why = withhold(emails[0].strip(), "%s %s" % (c["city"], seat_text))
                if email and not EMAIL_RE.match(email):
                    fail("%s %s: %r is not an e-mail address" % (c["city"], seat_text, email))
                if email:
                    rec["email"] = email
            rec["url"] = url
        ward_m = WARD_SEAT_RE.match(seat_text)
        if ward_m:
            ward = ward_m.group(1)
            if ward in wards:
                fail("%s: Ward %s is listed twice" % (c["city"], ward))
            rec["seat"] = "Ward %s" % ward
            wards[ward] = rec
        elif seat_text == AT_LARGE_SEAT:
            rec["seat"] = "At large"
            at_large.append(rec)
        else:
            fail("%s: a seat the page calls %r" % (c["city"], seat_text))
    # A number or address printed for two or more members, or equal to City
    # Hall's line, is the council's and no one person's (the fleet's rule), so
    # it rides nobody's row. None was, on 2026-11-02.
    hall_line = None
    hall_m = CITY_HALL_RE.search(re.sub(r"\s+", " ", text_of(body)))
    if hall_m:
        hall_line = "(%s) %s-%s" % (hall_m.group(3), hall_m.group(4), hall_m.group(5))
    members = list(wards.values()) + at_large
    seen_phone, seen_mail = {}, {}
    for r in members:
        for ph in r.get("phones", []):
            seen_phone[ph["number"]] = seen_phone.get(ph["number"], 0) + 1
        if r.get("email"):
            seen_mail[r["email"].lower()] = seen_mail.get(r["email"].lower(), 0) + 1
    for r in members:
        keep = [ph for ph in r.get("phones", [])
                if seen_phone[ph["number"]] == 1 and ph["number"] != hall_line]
        if len(keep) != len(r.get("phones", [])):
            print("%s %s: a telephone printed for more than one member, or City Hall's, "
                  "rides no one's row" % (c["city"], r["seat"]), file=sys.stderr)
        if keep:
            r["phones"] = keep
        else:
            r.pop("phones", None)
        if r.get("email") and seen_mail[r["email"].lower()] > 1:
            print("%s %s: an e-mail address printed for more than one member rides no one's "
                  "row" % (c["city"], r["seat"]), file=sys.stderr)
            r.pop("email")
    want = [str(n) for n in range(1, c["wards"] + 1)]
    if sorted(wards, key=int) != want:
        fail("%s: the page's wards are %s, not 1 to %d"
             % (c["city"], sorted(wards, key=int), c["wards"]))
    if len(at_large) != c["at_large"]:
        fail("%s: %d at-large seats, not %d" % (c["city"], len(at_large), c["at_large"]))
    unnamed = [r["seat"] for r in list(wards.values()) + at_large if not r["name"]]
    if len(unnamed) > c["max_unnamed"]:
        fail("%s: the page names no one for %d seats (%s)" % (c["city"], len(unnamed), unnamed))
    hall = CITY_HALL_RE.search(re.sub(r"\s+", " ", text_of(body)))
    if not hall:
        fail("%s: the page's Contact Us block no longer gives City Hall" % c["city"])
    office = {"label": "City Hall", "lines": [hall.group(1), hall.group(2)],
              "phone": "(%s) %s-%s" % (hall.group(3), hall.group(4), hall.group(5))}
    return {
        "city": c["city"],
        "body": c["body"],
        "source": c["page"],
        "office": office,
        "wards": {w: wards[w] for w in want},
        "atLarge": at_large,
    }, unnamed


def build(out_dir, offline=None, save=None):
    today = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    out = {}
    for c in CITIES:
        body = get_page(c["page"], offline, save)
        rec, unnamed = parse_council(body, c)
        rec["asOf"] = today
        out[c["geoid"]] = rec
        named = sum(1 for r in list(rec["wards"].values()) + rec["atLarge"] if r["name"])
        print("%s: %d of %d seats named%s" % (c["city"], named, c["wards"] + c["at_large"],
              "; the page names no one for " + ", ".join(unnamed) if unnamed else ""),
              file=sys.stderr)
    problems = check_data(out)
    if problems:
        fail("refusing to write:\n  " + "\n  ".join(problems))
    path = os.path.join(out_dir, OUT_NAME)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("wv-city-councils -> %s" % os.path.relpath(path, INSTANCE_ROOT), file=sys.stderr)


def _strings(value, key=""):
    """(key, string) for every string in a record, at any depth."""
    if isinstance(value, dict):
        for k, v in value.items():
            for item in _strings(v, k):
                yield item
    elif isinstance(value, list):
        for v in value:
            for item in _strings(v, key):
                yield item
    elif isinstance(value, str):
        yield key, value


def check_data(data):
    problems = []
    if sorted(data) != sorted(c["geoid"] for c in CITIES):
        problems.append("the file's cities are %s, not CITIES' %s"
                        % (sorted(data), sorted(c["geoid"] for c in CITIES)))
    for c in CITIES:
        rec = data.get(c["geoid"])
        if not rec:
            continue
        if rec.get("city") != c["city"] or rec.get("source") != c["page"]:
            problems.append("%s: the record's city or source is not CITIES'" % c["geoid"])
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", str(rec.get("asOf") or "")):
            problems.append("%s: no asOf date" % c["city"])
        wards = rec.get("wards") or {}
        if list(wards) != [str(n) for n in range(1, c["wards"] + 1)]:
            problems.append("%s: wards %s, not 1 to %d in order" % (c["city"], list(wards), c["wards"]))
        for w, r in wards.items():
            if r.get("seat") != "Ward %s" % w:
                problems.append("%s Ward %s carries seat %r" % (c["city"], w, r.get("seat")))
        at_large = rec.get("atLarge") or []
        if len(at_large) != c["at_large"] or any(r.get("seat") != "At large" for r in at_large):
            problems.append("%s: %d at-large seats, not %d" % (c["city"], len(at_large), c["at_large"]))
        seats = list(wards.values()) + at_large
        if sum(1 for r in seats if not r.get("name")) > c["max_unnamed"]:
            problems.append("%s: more than %d seats name no one" % (c["city"], c["max_unnamed"]))
        for r in seats:
            if not r.get("name") and set(r) - {"name", "seat"}:
                problems.append("%s %s names no one and carries %s"
                                % (c["city"], r.get("seat"), sorted(set(r) - {"name", "seat"})))
            for p in r.get("phones") or []:
                if not re.match(r"^\(\d{3}\) \d{3}-\d{4}$", p.get("number") or ""):
                    problems.append("%s %s: telephone %r is not one number"
                                    % (c["city"], r.get("seat"), p.get("number")))
                if p.get("label") not in (None, "Home", "Cell", "Office"):
                    problems.append("%s %s: telephone label %r" % (c["city"], r.get("seat"), p.get("label")))
            if r.get("email") and not EMAIL_RE.match(r["email"]):
                problems.append("%s %s: %r is not an e-mail address" % (c["city"], r.get("seat"), r["email"]))
            if set(r) - {"name", "seat", "phones", "email", "url"}:
                problems.append("%s %s carries %s" % (c["city"], r.get("seat"),
                                                     sorted(set(r) - {"name", "seat", "phones", "email", "url"})))
        phones = [p.get("number") for r in seats for p in r.get("phones") or []]
        mails = [r["email"].lower() for r in seats if r.get("email")]
        for v in sorted(set(x for x in phones if phones.count(x) > 1) |
                        set(x for x in mails if mails.count(x) > 1)):
            problems.append("%s: %r rides more than one member's row" % (c["city"], v))
        office = rec.get("office") or {}
        if office.get("phone") in phones:
            problems.append("%s: City Hall's line rides a member's row" % c["city"])
        if office.get("label") != "City Hall" or len(office.get("lines") or []) != 2:
            problems.append("%s: the council's office is not City Hall's two lines" % c["city"])
        # No street address anywhere but the council's own office.
        for key, s in _strings({k: v for k, v in rec.items() if k != "office"}):
            if STREET_RE.search(s):
                problems.append("%s: %r looks like a street address (in %s)" % (c["city"], s, key or "a list"))
    return problems


def check():
    path = os.path.join(DEFAULT_OUT_DIR, OUT_NAME)
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    problems = check_data(data)
    if problems:
        print("wv-city-councils --check: FAIL\n  " + "\n  ".join(problems), file=sys.stderr)
        return 1
    seats = sum(len(r["wards"]) + len(r["atLarge"]) for r in data.values())
    named = sum(1 for r in data.values() for s in list(r["wards"].values()) + r["atLarge"] if s["name"])
    print("wv-city-councils --check: OK (%d cities, %d of %d seats named, no street address)"
          % (len(data), named, seats))
    return 0


def main(argv):
    args = list(argv[1:])
    if "--check" in args:
        return check()
    offline = save = None
    for flag in ("--offline", "--save"):
        if flag in args:
            i = args.index(flag)
            if i + 1 >= len(args):
                fail("%s needs a directory" % flag)
            if flag == "--offline":
                offline = args[i + 1]
            else:
                save = args[i + 1]
            del args[i:i + 2]
    out_dir = args[0] if args else DEFAULT_OUT_DIR
    build(out_dir, offline, save)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
