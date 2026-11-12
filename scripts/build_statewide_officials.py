#!/usr/bin/env python3
"""
Build an app's Statewide officials roster: the officers its state elects
statewide (governor, lieutenant governor, attorney general and the rest) and
its two U.S. senators. Adam chose to name them in every app on 2026-11-10, as a line at the top of the results that opens into the full list.

WHERE THE NAMES COME FROM, AND HOW THEY STAY TRUE.

  State officers. Each app keeps a seed, <tag>/data/source/
  statewide-officials.source.json, listing the offices its state ELECTS
  statewide (an appointed office is never listed) with the officeholder's
  name as that officer's own government page prints it and that page's
  address. The names were read by a person from those pages. What keeps them
  true is this script: every run fetches each officer's page and REFUSES TO
  WRITE when the name is no longer on it. A January handover, a resignation or
  a death therefore turns the weekly job red, naming the office, instead of
  shipping a name the state no longer prints. The seed is edited by hand from
  the new page, which is the same reviewed step any roster change takes.

  A page that cannot be read this run (robots.txt refuses us, the host is
  down, a challenge) is NOT a page that dropped the name. That officer keeps
  the last record this script wrote, with the date it was last actually
  verified (Adam's preserve ruling of 2026-09-19), and the run says so. Only a
  page that was read and does not carry the name fails the build.

  U.S. senators. Read from the Senate's own list of senators
  (senate.gov's senators_cfm.xml), which names each senator with party,
  office, telephone and website, filtered to the app's state. Exactly two are
  required.

robots.txt is read before the first fetch of every host, with the client
that fetches (scraper_common.require_robots_once); a refusal is obeyed.

Usage:
    python3 scripts/build_statewide_officials.py --tag ky        # one app
    python3 scripts/build_statewide_officials.py                 # every app with a seed
    python3 scripts/build_statewide_officials.py --probe --tag ky  # report only, write nothing
    python3 scripts/build_statewide_officials.py --check         # offline: output matches seed
"""

import argparse
import datetime
import glob
import html
import json
import os
import re
import sys
import unicodedata
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from scraper_common import (  # noqa: E402
    UA_HEADERS_ROSTER_BOT,
    UA_ROSTER_BOT,
    require_robots_once,
)

SENATE_XML = "https://www.senate.gov/general/contact_information/senators_cfm.xml"
SEED_NAME = "statewide-officials.source.json"
OUT_NAME = "statewide-officials.json"

# A seed may set "headers": "browser" on an officer whose host refuses our
# token and serves a browser; the measurement goes in the seed's own "note".
BROWSER_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "identity",
    "sec-ch-ua": '"Chromium";v="126", "Not;A=Brand";v="24"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
}

SEED_TOP = {"state", "usps", "officersNote", "officers", "_comment"}
SEED_KEYS = {"office", "name", "url", "source", "match", "phone", "email",
             "headers", "note", "unnamed"}

# Suffixes a page may print or drop after a surname.
SUFFIXES = {"jr", "sr", "ii", "iii", "iv"}


class Unreadable(Exception):
    """The page could not be read this run; not evidence the name is gone."""


def seeds():
    out = {}
    for path in sorted(glob.glob(os.path.join(REPO_ROOT, "*", "data", "source", SEED_NAME))):
        tag = path.split(os.sep)[-4]
        out[tag] = path
    return out


def fold(text):
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.replace("’", "'").replace("‘", "'")
    text = re.sub(r"[. ]", " ", text)
    return re.sub(r"\s+", " ", text).strip().casefold()


def page_text(raw):
    raw = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", raw)
    # titles and alt text often carry the name on a governor's front page
    attrs = " ".join(re.findall(r'(?i)(?:alt|title|content|aria-label)="([^"]*)"', raw))
    body = re.sub(r"(?s)<[^>]+>", " ", raw)
    return fold(html.unescape(body + " " + attrs))


def fetch(url, headers):
    require_robots_once(url, headers["User-Agent"], headers=headers,
                        label="build-statewide-officials")
    req = urllib.request.Request(url, headers=dict(headers))
    try:
        with urllib.request.urlopen(req, timeout=40) as resp:
            body = resp.read()
    except urllib.error.HTTPError as exc:
        raise Unreadable("HTTP %d" % exc.code)
    except (urllib.error.URLError, OSError) as exc:
        raise Unreadable(str(getattr(exc, "reason", exc)))
    return body.decode("utf-8", "replace")


def verify_officer(rec):
    url = rec.get("source") or rec["url"]
    headers = BROWSER_HEADERS if rec.get("headers") == "browser" else UA_HEADERS_ROSTER_BOT
    try:
        text = page_text(fetch(url, headers))
    except SystemExit:  # scraper_common's robots refusal exits after saying why
        raise Unreadable("robots.txt refuses this client")
    if name_on_page(rec, text):
        return True
    # a challenge answered in the page's place says nothing about the name
    # (measured 2026-11-10: www.sos.state.mn.us served a Radware captcha page
    # after a few reads). It is never answered or worked around. It is asked
    # only once the name is missing, because a real page can say "captcha"
    # too: on 2026-11-12 portal.ct.gov/ag served the Attorney General's page,
    # naming him, with "please fill out the reCAPTCHA" in its newsletter form,
    # and asking the challenge question first called that page a challenge.
    # "The requested URL was rejected" is an F5 firewall's refusal page, which
    # ltgov.delaware.gov served in place of its page after a few reads on
    # 2026-11-12, having served the page itself minutes earlier.
    if len(text) < 8000 and re.search(r"captcha|are you a (?:ro)?bot|verify you are human|"
                                      r"attention required|just a moment|incapsula incident|"
                                      r"the requested url was rejected", text):
        raise Unreadable("a challenge page answered instead of the page")
    return False


def name_on_page(rec, text):
    if any(fold(w) in text for w in [rec["name"]] + list(rec.get("match") or [])):
        return True
    # "Abigail Spanberger" printed as "Abigail D. Spanberger": the given name,
    # up to two middle words, then the surname
    words = [w for w in fold(rec["name"]).replace(",", " ").split() if w not in SUFFIXES]
    if len(words) < 2:
        return False
    pat = r"\b%s(?: \S+){0,2} %s\b" % (re.escape(words[0]), re.escape(words[-1]))
    return re.search(pat, text) is not None


def senators(usps, xml_text):
    out = []
    for block in re.findall(r"(?s)<member>(.*?)</member>", xml_text):
        def f(tag):
            m = re.search(r"(?s)<%s>(.*?)</%s>" % (tag, tag), block)
            return html.unescape(m.group(1)).strip() if m else ""
        if f("state") != usps:
            continue
        party = {"R": "Republican", "D": "Democratic", "I": "Independent"}.get(f("party"), f("party"))
        # the Senate's list puts a suffix in the first name ("Angus S., Jr."
        # for Angus S. King, Jr.), so a plain join reads "Angus S., Jr. King"
        first, suffix = f("first_name"), ""
        m = re.match(r"^(.*?),\s*(Jr\.|Sr\.|II|III|IV)$", first)
        if m:
            first, suffix = m.group(1), m.group(2)
        rec = {
            "name": "%s %s%s" % (first, f("last_name"), ", " + suffix if suffix else ""),
            "_last": f("last_name"),
            "party": party,
            "url": f("website") or None,
            "office": f("address") or None,
            "phone": f("phone") or None,
        }
        out.append({k: v for k, v in rec.items() if v})
    out.sort(key=lambda r: r["_last"])
    for r in out:
        r.pop("_last", None)
    return out


def load_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def check_seed(tag, seed):
    problems = []
    for key in ("state", "usps", "officers"):
        if key not in seed:
            problems.append("%s: seed has no %r" % (tag, key))
    extra_top = set(seed) - SEED_TOP
    if extra_top:
        problems.append("%s: seed carries unknown keys %s" % (tag, sorted(extra_top)))
    offices = set()
    for rec in seed.get("officers", []):
        extra = set(rec) - SEED_KEYS
        if extra:
            problems.append("%s: %s carries unknown keys %s" % (tag, rec.get("office"), sorted(extra)))
        if rec.get("unnamed") and rec.get("name"):
            problems.append("%s: %s is unnamed and also names someone" % (tag, rec.get("office")))
        for key in (("office", "url") if rec.get("unnamed") else ("office", "name", "url")):
            if not rec.get(key):
                problems.append("%s: an officer has no %r" % (tag, key))
        if not str(rec.get("url", "")).startswith("https://"):
            problems.append("%s: %s url is not https" % (tag, rec.get("office")))
        key = (rec.get("office"), rec.get("name"))
        if key in offices:
            problems.append("%s: %s listed twice" % (tag, rec.get("office")))
        offices.add(key)
    return problems


def build(tag, seed_path, probe, xml_text, today):
    seed = load_json(seed_path)
    problems = check_seed(tag, seed)
    if problems:
        return problems
    out_path = os.path.join(REPO_ROOT, tag, "data", "app", OUT_NAME)
    prior = load_json(out_path) if os.path.exists(out_path) else {}
    prior_by = {(o["office"], o.get("name")): o for o in prior.get("officers", [])}
    officers, failures = [], []
    for rec in seed["officers"]:
        card = {k: rec[k] for k in ("office", "name", "url", "phone", "email") if rec.get(k)}
        if rec.get("unnamed"):
            # an office whose own pages refuse this project: listed, linked,
            # and named nowhere rather than named from memory
            card = {"office": rec["office"], "url": rec["url"], "unnamed": rec["unnamed"]}
            print("  %s %-34s listed without a name (%s)" % (tag, rec["office"], rec["unnamed"]))
            officers.append(card)
            continue
        try:
            ok = verify_officer(rec)
        except Unreadable as exc:
            old = prior_by.get((rec["office"], rec["name"]))
            print("  %s %-34s UNREADABLE (%s)%s" % (tag, rec["office"], exc,
                  ", keeping the record verified %s" % old["verified"] if old else ""))
            if not old:
                # never read, so nothing to keep: listed and linked, named
                # nowhere, and named on the first run that can read the page
                officers.append({"office": rec["office"], "url": rec["url"],
                                 "unnamed": "The office's own website could not be read "
                                            "when this list was built, so no name is shown "
                                            "until it can be."})
                continue
            card["verified"] = old["verified"]
            officers.append(card)
            continue
        print("  %s %-34s %s" % (tag, rec["office"], "ok" if ok else "NAME NOT ON PAGE"))
        if not ok:
            failures.append("%s: %s, %s is no longer on %s; read the page and update the seed"
                            % (tag, rec["office"], rec["name"], rec.get("source") or rec["url"]))
            continue
        card["verified"] = today
        officers.append(card)
    sens = senators(seed["usps"], xml_text)
    if len(sens) != 2:
        failures.append("%s: the Senate's list gives %d senators for %s, not 2"
                        % (tag, len(sens), seed["usps"]))
    if failures or probe:
        return failures
    out = {
        "_comment": ("Built by scripts/build_statewide_officials.py from %s/data/source/%s "
                     "and the Senate's list of senators. Do not edit by hand." % (tag, SEED_NAME)),
        "state": seed["state"],
        "usSenate": sens,
        "usSenateSource": "https://www.senate.gov/senators/",
        "usSenateRead": today,
        "officers": officers,
    }
    if seed.get("officersNote"):
        out["officersNote"] = seed["officersNote"]
    # keep the file byte-stable when nothing but the dates moved
    if prior and strip_dates(prior) == strip_dates(out):
        out = prior
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("  %s: wrote %d officers and %d senators" % (tag, len(officers), len(sens)))
    return []


def strip_dates(doc):
    doc = json.loads(json.dumps(doc))
    doc.pop("usSenateRead", None)
    for o in doc.get("officers", []):
        o.pop("verified", None)
    return doc


def check(tags):
    problems = []
    for tag, seed_path in tags.items():
        seed = load_json(seed_path)
        problems += check_seed(tag, seed)
        out_path = os.path.join(REPO_ROOT, tag, "data", "app", OUT_NAME)
        if not os.path.exists(out_path):
            problems.append("%s: seed exists but %s/data/app/%s does not; run the builder"
                            % (tag, tag, OUT_NAME))
            continue
        out = load_json(out_path)
        seed_offs, out_offs = seed["officers"], out.get("officers", [])
        if [r["office"] for r in seed_offs] != [r["office"] for r in out_offs]:
            problems.append("%s: the roster's offices differ from the seed's; run the builder" % tag)
        else:
            for want, got in zip(seed_offs, out_offs):
                # an officer whose page could not yet be read ships unnamed
                if got.get("name") != want.get("name") and not got.get("unnamed"):
                    problems.append("%s: %s is %r in the roster and %r in the seed; run the builder"
                                    % (tag, want["office"], got.get("name"), want.get("name")))
        for r in out.get("officers", []):
            if r.get("unnamed"):
                continue
            if not re.match(r"^\d{4}-\d{2}-\d{2}$", str(r.get("verified", ""))):
                problems.append("%s: %s carries no verified date" % (tag, r.get("office")))
        if len(out.get("usSenate", [])) != 2:
            problems.append("%s: the roster names %d U.S. senators, not 2"
                            % (tag, len(out.get("usSenate", []))))
        if out.get("state") != seed["state"]:
            problems.append("%s: roster state %r differs from seed %r" % (tag, out.get("state"), seed["state"]))
    return problems


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--tag", action="append", help="app tag (repeatable); default every app with a seed")
    ap.add_argument("--probe", action="store_true", help="verify and report; write nothing")
    ap.add_argument("--check", action="store_true", help="offline: each roster matches its seed")
    args = ap.parse_args()
    all_seeds = seeds()
    tags = {t: all_seeds[t] for t in (args.tag or all_seeds)} if args.tag else all_seeds
    missing = [t for t in (args.tag or []) if t not in all_seeds]
    if missing:
        sys.exit("no seed for %s" % ", ".join(missing))
    if args.check:
        problems = check(tags)
        if problems:
            print("\n".join("FAIL " + p for p in problems))
            sys.exit(1)
        print("OK: %d statewide officials rosters match their seeds" % len(tags))
        return
    today = datetime.date.today().isoformat()
    try:
        xml_text = fetch(SENATE_XML, UA_HEADERS_ROSTER_BOT)
    except Unreadable as exc:
        sys.exit("FAIL: the Senate's list of senators could not be read (%s)" % exc)
    failures = []
    for tag, path in tags.items():
        failures += build(tag, path, args.probe, xml_text, today)
    if failures:
        print("\n".join("FAIL " + f for f in failures))
        sys.exit(1)


if __name__ == "__main__":
    main()
