#!/usr/bin/env python3
"""
Scrape stage 1b: the three per-office sources that are BETTER than the ISAC
member portal, and cache them for build_ia_county_officers.py (stage 2).

ia_county_officers_scraper.py (stage 1a) reads one page per county from
member-portal.iowacounties.org and returns every elected officer at once --
but it publishes NO E-MAIL for anybody and is measurably wrong about some
supervisor counts. This file reads three sources that each cover exactly one
office statewide, and each adds something the portal cannot:

  RECORDER          iowalandrecords.org/recorder-directory/
                    The best-quality county source this project has found in
                    Iowa: one card per county with the recorder's name, role,
                    office phone and a plain mailto:, no obfuscation at all.
  SHERIFF           issda.org "2025 Sheriff Directory" (PDF, 4 April 2025)
  COUNTY ATTORNEY   iowa-icaa.com "@RosterOfCA&ACAs.pdf" (5 May 2026)

TREASURER IS DELIBERATELY ABSENT and that is a measurement, not an omission:
Iowa's county treasurers have no statewide directory. iowatreasurers.org is a
payment portal (vehicle registration and property tax), not a roster, and it
names nobody. The ISAC portal is the ONLY source for that office, which is why
the treasurer ships from stage 1a with no second witness -- recorded rather
than papered over.

WHY BOTH PDFs NEED pdfplumber AND NOT A LINE-FLATTENED READ
------------------------------------------------------------
Both documents are MULTI-COLUMN, and both defeat a flattened extraction in the
same way: `pdftotext -layout` interleaves the columns, so a county's own
sheriff ends up on a line with two other counties' text. Each parse below
therefore works from word COORDINATES (pdfplumber's extract_words) and
assigns every word to a column by its x0 before ever forming a line.

  ISSDA: a 4-column magazine layout, gutters measured at x0 = 153 / 293 / 437
  on a 612pt page. Entries flow down a column and continue across pages.
  ICAA:  3 columns -- address/telephone (x0 < 235), COUNTY ATTORNEY
  (235 <= x0 < 372) and ASSISTANTS (x0 >= 372).

THE ASSISTANTS COLUMN MUST NEVER BE READ. Assistant county attorneys are
APPOINTED, not elected; a naive regex over a flattened ICAA line returns
"ANTHONY GERICKE Jill Kistler" and would ship an appointed staff member on a
card that is about elected representation. The x-band is what excludes them.

EIGHT MEASURED TRAPS, each guarded below:

1. THE ISSDA COUNTY HEADER IS NOT RELIABLY UPPER-CASE OR ASCII. 97 of the 99
   headers read like "ADAIR 01"; the other two are "O’BRIEN 71" (a U+2019
   RIGHT SINGLE QUOTATION MARK, not an ASCII apostrophe) and "Van Buren 89"
   (the single title-case header in the document). An `[A-Z']` header pattern
   drops both SILENTLY. Every header carries the county's own alphabetical
   index 01-99, so this parse gates on recovering the COMPLETE set 1..99 --
   which is what turned both misses into a failure instead of a short file.

2. THE ISSDA SHERIFF NAME IS SOMETIMES ON THE NEXT LINE. 94 entries read
   "Sheriff Jeff Vandewater"; 5 (Cerro Gordo, Lee, Mahaska, Plymouth, Wright)
   put "Sheriff" or "Sheriff:" alone on its own line with the name below it.

3. ISSDA E-MAIL WRAPS ACROSS LINES, and one entry is letter-spaced. Addresses
   are published as "Email: d.upah@" / "bentonsheriff.com", and Wright's whole
   block is tracked out to "E m a i l : js c h l u tt @" / "co.wright.ia.us".
   Both are recovered by joining the continuation lines and removing ALL
   whitespace -- but the join MUST stop at the next field label, or
   "Dhepperly@" + "cerrogordo.gov" + "Station ID No. S171" glues into one
   string that still matches an e-mail regex and is wrong. 15 of the 99
   entries publish no e-mail at all; those ship without one.

4. THE ICAA COUNTY LINE IS NOT ALWAYS EXACTLY "<NAME> COUNTY". Three of the 99
   carry trailing text on the same line, so the left-column match is a PREFIX
   match; an anchored full-line match returns 96 and looks like a healthy run.

5. iowa-icaa.com ANSWERS 404 WITH A FULL PAGE BODY -- its 404 serves the same
   ~40 KB of navigation as its home page, PDF links and all. Nothing here
   reads that page (the roster URL is pinned), but it is the same "a 200 is
   not a document, and a 404 is not an empty one" shape the ISAC portal has,
   and it is why every parse below gates on CONTENT COUNTS, never on status.

6. AN ALL-CAPS TEST FOR THE ICAA NAME IS WRONG THREE WAYS. "TY A. STEWART (J)"
   trails an ICAA designation, "MARCUS GROSS, JR." carries a comma, and
   "NOLAN McGOWAN" is genuinely mixed case -- while the test still has to
   reject the Title-Case ASSISTANTS. Upper-case DOMINANCE separates them
   (McGOWAN 6 upper to 1 lower; "Kistler" 1 to 6). See _icaa_name_token.

8. THE ISSDA SHERIFF'S NAME ITSELF CAN WRAP. Sioux County prints "Sheriff
   Jamie Van" / "Voorst" on two lines; stopping at the break ships "Jamie Van",
   a half surname that looks like a whole one and raises no error anywhere.

7. THE ICAA ATTORNEY NAME CAN SIT ABOVE ITS OWN COUNTY LINE. It is set in a
   larger face, so its baseline is up to ~3pt HIGHER than the county heading
   beside it -- Franklin's "ANDREA MILLER" is at top 647.4 against "FRANKLIN
   COUNTY" at 650.2. Any parse that reads a county's block as the lines
   FOLLOWING its header cannot see that name at all, and loses it silently.
   The block is therefore a vertical WINDOW that starts ICAA_LOOKBACK points
   ABOVE the heading and runs to just above the next county's.

ADDRESSES ARE READ FOR CONTACT AND NEVER AS TEXT. Both PDFs print an address
block per officer -- the ICAA's is a mix of courthouse and private-law-office
addresses. This scraper reads those lines ONLY to pull a phone number and an
e-mail out of them and never keeps the line itself, so no address from either
document can reach a card. The County card's office block continues to come
from the auditors' association, which publishes courthouse addresses only.

Usage:
    python3 ia/scripts/ia_county_officer_sources_scraper.py
"""

import html
import io
import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(_HERE)),
                                "scripts"))
from scraper_common import UA_ROSTER_BOT, require_robots_once  # noqa: E402  (FLEET_SHARED)

try:
    import requests
except ImportError:
    print("FATAL: pip install -r ia/scripts/requirements.txt", file=sys.stderr)
    sys.exit(1)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # ia/
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache")
OUT_FILE = os.path.join(CACHE_DIR, "ia_county_officer_sources.json")
COUNTIES_FILE = os.path.join(REPO_ROOT, "data", "app", "state-counties.json")

RECORDER_URL = "https://iowalandrecords.org/recorder-directory/"
SHERIFF_PDF_URL = "https://www.issda.org/assets/Gold-Star/2025%20Sheriff%20Directory.pdf"
ATTORNEY_PDF_URL = "https://iowa-icaa.com/Roster/%40RosterOfCA%26ACAs.pdf"

EXPECT_COUNTIES = 99
# Floors, not targets. Each is set below the count measured on 2026-08-28
# (recorder 99, sheriff 99, county attorney 99) with room for a county whose
# entry is mid-edit, and far enough above zero that a reshaped page fails.
MIN_RECORDERS = 95
MIN_SHERIFFS = 95
MIN_ATTORNEYS = 95

# THE TOKEN, NOT A BROWSER STRING, AND THAT IS A MEASUREMENT.
# This file sent a Chrome/120 string with no client hints, which no measurement
# ever licensed: user-agent-measurements.json records all three of its hosts
# `token-ok` AT THE EXACT URL EACH IS FETCHED FROM, with a full document each
# (iowalandrecords.org 649,498 bytes, www.issda.org 951,591, iowa-icaa.com
# 469,414) — measured at the page the scraper reads, never at a directory above
# it. Sending a browser string to a host that serves the token is unlicensed on
# its own, and here it also broke the fleet's consistency rule: robots.txt must
# be read with the EXACT client that will crawl, and the runner measurement in
# robots-verdicts.json reads these hosts as the token. One client for both, so
# the policy that is read is the policy that governs the fetch.
# Re-measured with the token on 2026-09-30, each at its own URL: recorder
# directory HTTP 200 / 649,506 bytes and the scraper's own parse 99 of 99
# counties, sheriff directory HTTP 200 / 951,591 bytes of PDF, county-attorney
# roster HTTP 200 / 464,278 bytes of PDF.
HEADERS = {"User-Agent": UA_ROSTER_BOT}
REQUEST_TIMEOUT = 90

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"\(?\d{3}\)?[\s.-]*\d{3}[\s.-]*\d{4}")


def fetch(url, binary=False):
    require_robots_once(url, HEADERS["User-Agent"], headers=HEADERS,
                        label="ia-ia-county-officer-sources-scraper")
    resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    if resp.status_code != 200:
        raise SystemExit("%s: HTTP %d" % (url, resp.status_code))
    return resp.content if binary else resp.text


def strip_tags(fragment):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def norm_county(raw):
    """Fold a source's county spelling to the shipped BASENAME's own key.

    Sources write ADAIR / Adair / ADAIR COUNTY / O’BRIEN / Van Buren; the
    typographic apostrophe (trap 1) is folded to ASCII here so it can never
    reach a comparison.
    """
    s = html.unescape(raw or "").replace("’", "'").strip().upper()
    s = re.sub(r"\s+COUNTY\s*$", "", s)
    return re.sub(r"\s+", " ", s).strip()


def county_lookup():
    with open(COUNTIES_FILE) as f:
        feats = json.load(f)["features"]
    lut = {norm_county(f["properties"]["BASENAME"]): f["properties"]["BASENAME"]
           for f in feats}
    if len(lut) != EXPECT_COUNTIES:
        raise SystemExit("state-counties.json carries %d counties, expected %d"
                         % (len(lut), EXPECT_COUNTIES))
    return lut


def require(kind, rows, floor, lut):
    unknown = sorted(set(rows) - set(lut.values()))
    if unknown:
        raise SystemExit("%s: %d county name(s) not in state-counties.json: %s"
                         % (kind, len(unknown), ", ".join(unknown[:6])))
    if len(rows) < floor:
        raise SystemExit("%s: parsed %d counties, floor %d -- the page or document "
                         "reshaped, or a column band moved" % (kind, len(rows), floor))
    print("%-16s %d counties (floor %d)" % (kind, len(rows), floor), file=sys.stderr)


# ---------------------------------------------------------------- recorders

def scrape_recorders(lut):
    text = fetch(RECORDER_URL)
    blocks = re.split(r'<h3 class="et_pb_toggle_title">', text)[1:]
    out = {}
    for blk in blocks:
        head, _, rest = blk.partition("</h3>")
        key = norm_county(strip_tags(head))
        if key not in lut:
            continue
        name = re.search(r'<div class="rec-name">(.*?)</div>', rest, re.S)
        if not name:
            continue
        rec = {"name": strip_tags(name.group(1))}
        role = re.search(r'<div class="rec-role">(.*?)</div>', rest, re.S)
        if role:
            rec["role"] = strip_tags(role.group(1))
        tel = re.search(r'href="tel:([^"]+)"[^>]*>(.*?)</a>', rest, re.S)
        if tel:
            rec["phone"] = strip_tags(tel.group(2)) or strip_tags(tel.group(1))
        mail = re.search(r'href="mailto:([^"?]+)', rest)
        if mail:
            rec["email"] = html.unescape(mail.group(1)).strip()
        if rec["name"]:
            out[lut[key]] = rec
    require("recorder", out, MIN_RECORDERS, lut)
    return out


# ----------------------------------------------------------------- sheriffs

# Trap 1: title case and U+2019 both appear in real headers.
ISSDA_HDR = re.compile(r"^([A-Za-z][A-Za-z’' ]{2,20}?)\s+(\d{2})$")
ISSDA_COLUMNS = [0, 153, 293, 437, 10000]
# Trap 3: the e-mail join stops at the next field label.
ISSDA_STOP = re.compile(
    r"^\s*(Station|Address|Support|Phone|Fax|Jail|ORI|www\.|http|Website|Chief|"
    r"Ch\.|Lt\.|Capt|Sgt|Sheriff|First|Deputy|•)", re.I)


def _pdf_lines(pdf_bytes, bounds):
    """Words -> (page, column, line) tuples, column assigned by x0 BEFORE the
    line is formed. This is the whole reason pdfplumber is required."""
    import pdfplumber
    rows = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for pi, page in enumerate(pdf.pages):
            cols = {}
            for w in page.extract_words():
                c = next(i for i in range(len(bounds) - 1)
                         if bounds[i] <= w["x0"] < bounds[i + 1])
                cols.setdefault(c, []).append(w)
            for c in sorted(cols):
                lines = {}
                for w in cols[c]:
                    lines.setdefault(round(w["top"] / 3.0), []).append(w)
                for k in sorted(lines):
                    txt = " ".join(x["text"] for x in
                                   sorted(lines[k], key=lambda z: z["x0"])).strip()
                    rows.append((pi, c, txt))
    return rows


def scrape_sheriffs(lut):
    rows = _pdf_lines(fetch(SHERIFF_PDF_URL, binary=True), ISSDA_COLUMNS)
    out, seen_index = {}, {}
    for i, (pi, c, text) in enumerate(rows):
        m = ISSDA_HDR.match(text)
        if not m:
            continue
        key = norm_county(m.group(1))
        if key not in lut:
            continue
        seen_index[int(m.group(2))] = key
        # the county's own block: forward within the same page-column only
        block = []
        for pj, cj, tj in rows[i + 1:]:
            if (pj, cj) != (pi, c) or ISSDA_HDR.match(tj):
                break
            block.append(tj)
        rec = {}
        for j, line in enumerate(block):
            mm = re.match(r"^Sheriff[:\s]*(.*)$", line)
            if not mm:
                continue
            name = mm.group(1).strip()
            used = j
            if not name and j + 1 < len(block):
                name = block[j + 1].strip()   # trap 2
                used = j + 1
            # Trap 8: the name itself WRAPS. Sioux reads "Sheriff Jamie Van" /
            # "Voorst", and a parse that stops at the line break ships "Jamie
            # Van" -- a real person's surname, cut in half, with no error
            # anywhere. A continuation is the next line only when it is a short
            # capitalised fragment that is not the next field label.
            if used + 1 < len(block):
                tail = block[used + 1].strip()
                if (tail and not ISSDA_STOP.match(tail) and len(tail.split()) <= 2
                        and re.fullmatch(r"[A-Z][A-Za-z’'\-]*(?: [A-Z][A-Za-z’'\-]*)?", tail)):
                    name = (name + " " + tail).strip()
            name = re.sub(r"\s+", " ", name).strip(" ,")
            if name and not ISSDA_STOP.match(name):
                rec["name"] = name
            break
        # Recorded ONLY so build_ia_county_officers.py can detect the ISAC
        # portal naming an APPOINTED deputy as the sheriff (measured in
        # Crawford, Page and Sioux). Never shipped: deputies are not elected.
        # The WHOLE block, capped -- deputy titles and their names wrap across
        # lines too ("Chief Deputy: Nate" / "Huizenga"), so a label-line filter
        # loses exactly the surname the test needs.
        rec["blockText"] = " ".join(block)[:400]
        email = _issda_email(block)
        if email:
            rec["email"] = email
        for line in block:
            if re.match(r"^\s*Phone", line, re.I):
                pm = PHONE_RE.search(line)
                if pm:
                    rec["phone"] = re.sub(r"\s+", " ", pm.group(0)).strip()
                break
        if rec.get("name"):
            out[lut[key]] = rec
    missing = sorted(set(range(1, EXPECT_COUNTIES + 1)) - set(seen_index))
    if missing:
        raise SystemExit(
            "sheriff: the directory's own alphabetical index 1..99 is incomplete -- "
            "missing %s. Two headers are not upper-case ASCII (O’BRIEN uses "
            "U+2019, Van Buren is title case); a stricter header pattern drops them "
            "silently." % missing)
    require("sheriff", out, MIN_SHERIFFS, lut)
    return out


def _continues_domain(rest):
    """Does the next line continue the domain rather than start a new field?

    A DOMAIN CAN WRAP AT A DOT, and `EMAIL_RE`'s TLD class is any run of two or
    more letters — so a block reading

        "Email: jsmith@" / "monroecounty.iowa" / ".gov"

    forms a perfectly valid-looking `jsmith@monroecounty.iowa` after the second
    line and would stop there, shipping a truncated domain with every guard
    green. That is not hypothetical here: it is the exact shape of Monroe's
    withheld address, whose real domain IS monroecounty.iowa.gov.

    A LEADING DOT IS THE DISCRIMINATOR, and it is what separates this from the
    four glued cases the stop-on-whole rule exists for: Clay's next line is
    `claycountysheriffsoffice.com`, a separate token that must NOT be joined,
    while `.gov` cannot begin a field and can only continue what precedes it.
    """
    for line in rest:
        return re.sub(r"\s+", "", line or "").startswith(".")
    return False


def _issda_email(block):
    """Trap 3: join wrapped continuation lines, stopping at the next label,
    then delete ALL whitespace (Wright's block is letter-spaced).

    THE JOIN STOPS THE MOMENT IT HAS A WHOLE ADDRESS, and that is the half this
    lacked until 2026-09-04. Trap 3 above predicted the failure exactly —
    "the join MUST stop at the next field label, or `Dhepperly@` +
    `cerrogordo.gov` + `Station ID No. S171` glues into one string that still
    matches an e-mail regex and is wrong" — and ISSDA_STOP was the guard
    written for it. A LABEL LIST CANNOT BE THE GUARD, because the line after
    the domain is often not a label at all. Four addresses shipped glued:

        Clay      'Email:' / 'craveling@claycounty.iowa.gov'
                            / 'claycountysheriffsoffice.com'   <- a WEBSITE
        Crawford  'Email: jsteinkuehler@' / 'crawfordso.net'
                            / 'Office Admin. & Assist.'
        Delaware  'Email: themesath@' / 'delawarecountyia.us'
                            / '1225 W. Howard St, Manchester IA 52057'
        Jones     'Email: greg.graver@' / 'jonescountyiowa.gov'
                            / 'State ID No. S531 ORI# IA0530000'

    None of those third lines starts with a word any label list would carry,
    and the greedy `[A-Za-z0-9.-]+` domain swallows all four — producing
    addresses that look alive, pass every count guard, and cannot receive mail.
    Completeness is the real test and it is self-maintaining: append a line,
    and return as soon as what you have IS an address. Clay's website and
    Jones's state id are never reached.

    It also declines correctly where the SOURCE is at fault. Monroe publishes
    `Email: @` with no local part at all, so nothing here forms an address and
    the county ships without one, which is the honest outcome.

    The trailing search() is kept for the shape this cannot see — a
    continuation line carrying the domain AND trailing junk, where no prefix is
    ever a whole address. It is now only reached in that case.
    """
    for j, line in enumerate(block):
        flat = re.sub(r"\s+", "", line)
        if not flat.lower().startswith("email"):
            continue
        window = [n for n in block[j + 1:j + 3]]
        parts = [flat.split(":", 1)[1] if ":" in flat else ""]
        if EMAIL_RE.fullmatch(parts[0]) and not _continues_domain(window[:1]):
            return parts[0]                      # whole address on the label line
        for k, nxt in enumerate(window):
            if ISSDA_STOP.match(nxt):
                break
            parts.append(re.sub(r"\s+", "", nxt))
            joined = "".join(parts)
            if EMAIL_RE.fullmatch(joined) and not _continues_domain(window[k + 1:k + 2]):
                return joined                    # whole, and nothing extends it
        m = EMAIL_RE.search("".join(parts))
        if m:
            return m.group(0)
    # Buena Vista publishes a bare address with no "Email:" label at all.
    for line in block:
        flat = re.sub(r"\s+", "", line)
        if EMAIL_RE.fullmatch(flat):
            return flat
    return None


# --------------------------------------------------------- county attorneys

ICAA_ATT_LO, ICAA_ATT_HI = 235.0, 372.0     # the ASSISTANTS column starts above ICAA_ATT_HI
ICAA_CTY = re.compile(r"^([A-Z][A-Z’\'. ]*?)\s+COUNTY\b")   # trap 4: PREFIX, not full-line
# Trap 7 (below): the name sits up to ~3pt ABOVE its own county line, so the
# block is a vertical WINDOW, not a run of following lines.
ICAA_LOOKBACK = 6.0


def _icaa_name_token(tok):
    """Is this band token part of an ALL-CAPS county-attorney name?

    Trap 6: the obvious test -- every character upper-case -- is wrong three
    ways in this document. "(J)" and "(MC)" are ICAA designations that trail a
    name, "GROSS," carries a comma, and "McGOWAN" is genuinely mixed case. The
    rule that survives all three while still rejecting the Title-Case
    ASSISTANTS ("Jill Kistler", "Todd Argotsinger") is upper-case DOMINANCE:
    McGOWAN is 6 upper to 1 lower, Kistler is 1 to 6. The x-band already
    excludes the assistants; this is the second guard, not the first.
    """
    letters = [c for c in tok if c.isalpha()]
    if not letters:
        return bool(re.fullmatch(r"[(),.\'’\-]+", tok))
    upper = sum(1 for c in letters if c.isupper())
    return upper >= len(letters) - upper


def scrape_county_attorneys(lut):
    import pdfplumber
    pdf_bytes = fetch(ATTORNEY_PDF_URL, binary=True)
    out = {}
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            words = page.extract_words()
            # county header lines, by the top of their LEFT-column text
            heads = []
            lines = {}
            for w in words:
                lines.setdefault(round(w["top"] / 3.0), []).append(w)
            for k in sorted(lines):
                ws = sorted(lines[k], key=lambda z: z["x0"])
                left = " ".join(w["text"] for w in ws if w["x0"] < ICAA_ATT_LO).strip()
                m = ICAA_CTY.match(left)
                if m and norm_county(m.group(1)) in lut:
                    heads.append((min(w["top"] for w in ws), norm_county(m.group(1))))
            heads.sort()
            for idx, (top, key) in enumerate(heads):
                lo = top - ICAA_LOOKBACK
                hi = heads[idx + 1][0] - ICAA_LOOKBACK if idx + 1 < len(heads) else 1e9
                block = [w for w in words if lo <= w["top"] < hi]
                # --- name: the attorney band only. The ASSISTANTS column is
                # NEVER read -- assistants are appointed, not elected.
                band = {}
                for w in block:
                    if ICAA_ATT_LO <= w["x0"] < ICAA_ATT_HI:
                        band.setdefault(round(w["top"] / 3.0), []).append(w)
                parts = []
                for bk in sorted(band):
                    toks = [w["text"] for w in sorted(band[bk], key=lambda z: z["x0"])]
                    if not all(_icaa_name_token(t) for t in toks):
                        break
                    parts += toks
                name = re.sub(r"\s*\([A-Z]{1,3}\)\s*$", "", " ".join(parts).strip()).strip()
                name = name.strip(",")
                if not name:
                    continue
                rec = {"name": name}
                # --- contact: the address block is read for a phone and an
                # e-mail ONLY, and the line itself is never kept, so no address
                # from this document can reach a card.
                addr = {}
                for w in block:
                    if w["x0"] < ICAA_ATT_LO:
                        addr.setdefault(round(w["top"] / 3.0), []).append(w)
                for ak in sorted(addr):
                    line = " ".join(w["text"] for w in sorted(addr[ak], key=lambda z: z["x0"]))
                    if "phone" not in rec:
                        pm = PHONE_RE.search(re.split(r"FAX", line, 1, re.I)[0])
                        if pm:
                            rec["phone"] = pm.group(0).strip()
                    if "email" not in rec:
                        em = EMAIL_RE.search(line)
                        if em:
                            rec["email"] = em.group(0)
                # Recorded ONLY so the builder can detect the ISAC portal
                # naming an APPOINTED assistant as the county attorney. The
                # assistants column is never shipped and never read for a name.
                asst = []
                for w in sorted(block, key=lambda z: (z["top"], z["x0"])):
                    if w["x0"] >= ICAA_ATT_HI:
                        asst.append(w["text"])
                if asst:
                    rec["assistantText"] = " ".join(asst[:24])
                out[lut[key]] = rec
    require("county attorney", out, MIN_ATTORNEYS, lut)
    return out


def main():
    os.makedirs(CACHE_DIR, exist_ok=True)
    lut = county_lookup()
    payload = {
        "recorder": scrape_recorders(lut),
        "sheriff": scrape_sheriffs(lut),
        "countyAttorney": scrape_county_attorneys(lut),
        "sources": {
            "recorder": RECORDER_URL,
            "sheriff": SHERIFF_PDF_URL,
            "countyAttorney": ATTORNEY_PDF_URL,
        },
    }
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=1, ensure_ascii=False, sort_keys=True)
    for office in ("recorder", "sheriff", "countyAttorney"):
        rows = payload[office]
        print("%-16s name %d | phone %d | email %d" % (
            office, len(rows),
            sum(1 for r in rows.values() if r.get("phone")),
            sum(1 for r in rows.values() if r.get("email"))), file=sys.stderr)
    print("wrote %s" % OUT_FILE, file=sys.stderr)


if __name__ == "__main__":
    main()
