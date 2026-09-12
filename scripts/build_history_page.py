#!/usr/bin/env python3
"""
Generate each instance's deployment-history page — the reader-facing account
of how an instance grew and how current its data actually is.

WHY THIS PAGE IS GENERATED. The strongest trust-building material this
project produces — what ships, what is checked on a schedule, which
corrections the machinery caught — otherwise lives in repo docs a reader
never sees, and a hand-written page about it would drift the week it
shipped (the numbers in it moved three times on the day this generator was
written). So the page splits its claims by how they can stay true:

  * FACTS ARE MEASURED at generation time from the files that own them —
    layer counts from the worksheet's layers[], refresh jobs from
    workflows[], recorded gaps from the shipped coverage-gaps.json, and any
    per-instance metric the worksheet declares against a shipped data file.
    They regenerate with every change and `--check` fails CI on drift.
  * NARRATIVE IS DATED, APPEND-ONLY. The changelog entries in the
    worksheet's history_page.entries each carry their own date and are
    rendered as snapshots ("as of" that day), so prose never claims a
    currency it does not have — the same posture the county card's own
    dated rows take. The generator refuses entries out of date order.

OPT-IN PER INSTANCE, like sources_page: a worksheet without a
`history_page` key generates nothing, and `--check` fails if an orphaned
history file exists without the key that owns it. The declared metrics
vocabulary is deliberately tiny (keys / features / sum:<field> /
count-nonzero:<field>) so a metric can only ever restate a shipped file.

Usage:
    python3 scripts/build_history_page.py            # (re)generate in place
    python3 scripts/build_history_page.py --check    # the CI drift gate
"""

import datetime
import json
import os
import re
import sys
import urllib.parse

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def shared_footer_byline(indent=""):
    """The author byline, read from its ONE source.

    engine/shared/footer-byline.txt is shared with the nineteen authored pages
    that carry it as an ENGINE fence spliced by compose_app.py. A GENERATED page
    reads it here instead of carrying a fence, because a fence would have to
    agree with whatever this builder emits inside it -- which means reading the
    file anyway, with an ordering dependency between the two tools on top. One
    source, two mechanisms; that file's own comment says the same thing from the
    other side.

    The block's leading HTML comment is for a reader of the engine tree and is
    dropped here, so the published page carries the markup alone.
    """
    path = os.path.join(REPO_ROOT, "engine", "shared", "footer-byline.txt")
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    markup = re.sub(r"(?s)^\s*<!--.*?-->\s*", "", text).strip()
    return "\n".join(indent + ln.strip() for ln in markup.splitlines())

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# One parser for the token/font/mark files, owned by the landing-page module
# (the privacy page's reasoning: a rename fails under the module that owns
# the file, not a mislabelled copy).
from build_landing_page import (  # noqa: E402
    FAVICON, FONTFACE, TOKENS, parse_token_block, read, token_css,
)
from build_privacy_page import (  # noqa: E402
    DARK_EXTRA, DARK_TOKENS, LIGHT_TOKENS, esc, fail,
)

# app dir -> worksheet path, matching generate_metro_files.py's INSTANCES
# (the reference instance's worksheet lives at the repo ROOT, not under il/)
INSTANCES = (("il", "metro-worksheet.json"),
             ("ca", "ca/metro-worksheet.json"),
             ("ny", "ny/metro-worksheet.json"),
             ("wi", "wi/metro-worksheet.json"),
             ("ia", "ia/metro-worksheet.json"),
             ("mi", "mi/metro-worksheet.json"))

METRIC_RE = re.compile(r"^(keys|features|sum:[A-Za-z]+|count-nonzero:[A-Za-z]+)$")
GROUP_ORDER = ("political", "safety", "schools", "geography")
GROUP_LABEL = {"political": "political", "safety": "public safety",
               "schools": "schools", "geography": "geography"}


def load_worksheet(worksheet_rel):
    path = os.path.join(REPO_ROOT, worksheet_rel)
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def measure_metric(inst, spec):
    path = os.path.join(REPO_ROOT, inst, spec["file"])
    if not os.path.exists(path):
        fail("%s: metric %r names %s, which does not exist"
             % (inst, spec["label"], spec["file"]))
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    metric = spec["metric"]
    if not METRIC_RE.match(metric):
        fail("%s: metric %r uses unknown measure %r" % (inst, spec["label"], metric))
    if metric == "keys":
        if not isinstance(data, dict):
            fail("%s: %s is not an object — 'keys' cannot count it" % (inst, spec["file"]))
        return len(data)
    if metric == "features":
        feats = data.get("features") if isinstance(data, dict) else None
        if not isinstance(feats, list):
            fail("%s: %s carries no features[] — 'features' cannot count it"
                 % (inst, spec["file"]))
        return len(feats)
    op, field = metric.split(":", 1)
    if not isinstance(data, dict):
        fail("%s: %s is not an object — '%s' cannot walk it" % (inst, spec["file"], op))
    values = [v.get(field) for v in data.values() if isinstance(v, dict)]
    if op == "sum":
        return sum(v for v in values if isinstance(v, (int, float)))
    return sum(1 for v in values if v)


def pretty_date(iso):
    d = datetime.date.fromisoformat(iso)
    return d.strftime("%d %B %Y").lstrip("0")


def stat_tiles(tiles):
    cells = []
    for label, value, note in tiles:
        cells.append(
            '<div class="tile"><div class="tile-n">%s</div>'
            '<div class="tile-l">%s</div>%s</div>'
            % (esc("{:,}".format(value) if isinstance(value, int) else str(value)),
               esc(label),
               ('<div class="tile-s">%s</div>' % esc(note)) if note else ""))
    return '<div class="tiles">%s</div>' % "".join(cells)


def build_instance(inst, w):
    cfg = w["history_page"]
    metro_name = w["metro_name"]
    # The name a READER sees is brand.app_name — the key that already owns every
    # reader-facing surface (the wordmark, sources.html's title, og:site_name).
    # It is NOT metro_name, which is the engine's internal handle for the fork and
    # is the one value free to disagree with the brand: Illinois's worksheet still
    # says "Chicago" there — a true record of where the app started, and wrong on a
    # page whose own footer links "districtry Illinois". Taking the product word
    # off the front of app_name leaves the place name, which keeps every instance
    # whose two names already agree byte-identical and fixes the one where they
    # never did.
    brand = w.get("brand") or {}
    product = brand.get("product_name") or "districtry"
    app_name = brand.get("app_name") or ("%s %s" % (product, metro_name))
    place = (app_name[len(product):].strip()
             if app_name.startswith(product) else metro_name)
    mine = next((m for m in w["metro_explorers"]
                 if m["id"] == w["this_metro"] or m.get("label") == metro_name), None)
    if mine is None:
        fail("%s: no metro_explorers entry matches this_metro %r"
             % (inst, w["this_metro"]))
    app_url = mine["url"]
    canonical = app_url + cfg["file"]

    dates = [e["date"] for e in cfg["entries"]]
    if dates != sorted(dates, reverse=True):
        fail("%s: history entries must be newest-first (dates non-increasing); "
             "got %s" % (inst, dates))

    layers = w["layers"]
    group_counts = []
    for g in GROUP_ORDER:
        n = sum(1 for l in layers if l["group"] == g)
        if n:
            group_counts.append("%d %s" % (n, GROUP_LABEL[g]))
    gaps_path = os.path.join(REPO_ROOT, inst, "data", "app", "coverage-gaps.json")
    n_gaps = None
    if os.path.exists(gaps_path):
        with open(gaps_path, encoding="utf-8") as f:
            gaps = json.load(f)
        if isinstance(gaps, dict):
            n_gaps = len(gaps)

    tiles = [("map layers", len(layers), " · ".join(group_counts)),
             ("scheduled refresh & audit jobs", len(w.get("workflows", [])),
              "each lands as a reviewed change, never silently")]
    for spec in cfg.get("metrics", []):
        tiles.append((spec["label"], measure_metric(inst, spec), spec.get("note")))
    if n_gaps is not None:
        tiles.append(("recorded data gaps", n_gaps,
                      "what the publishers withhold, on the record in the app"))

    entries_html = []
    for e in cfg["entries"]:
        entries_html.append(
            '<li class="entry"><div class="entry-date">%s</div>'
            '<h3>%s</h3><p>%s</p></li>'
            % (esc(pretty_date(e["date"])), esc(e["title"]), esc(e["body"])))

    workflow_rows = []
    for job in w.get("workflows", []):
        workflow_rows.append(
            "<tr><td>%s</td><td><code>%s</code></td><td>%s</td></tr>"
            % (esc(job["purpose"]), esc(job["file"]), esc(job["schedule"])))

    tokens_css = read(TOKENS, "the design tokens")
    light = parse_token_block(tokens_css, ":root", TOKENS)
    dark = parse_token_block(tokens_css, '[data-theme="dark"]', TOKENS)
    favicon = read(FAVICON, "the brand mark").strip()
    if not favicon.startswith("<svg"):
        fail("favicon.svg does not start with <svg — is it still an SVG?")
    favicon_uri = "data:image/svg+xml," + urllib.parse.quote(favicon, safe="")
    fontface = read(FONTFACE, "the self-hosted font CSS").rstrip("\n")

    title = "History — %s" % app_name
    # 155 characters at the longest place name (Wisconsin), measured — see
    # scripts/validate_serp_lengths.py. Trimmed from the FRONT so the tail,
    # which is what distinguishes this page from every other changelog,
    # survives truncation.
    desc = ("How the %s deployment grew and what it checks on a schedule — "
            "dated, measured, and regenerated with every change." % place)

    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>%(title)s</title>
<meta name="description" content="%(desc)s" />
<meta name="robots" content="index, follow" />
<link rel="canonical" href="%(canonical)s" />
<link rel="icon" href="%(favicon)s" type="image/svg+xml" />
<meta property="og:type" content="article" />
<meta property="og:site_name" content="%(app_name)s" />
<meta property="og:title" content="%(title)s" />
<meta property="og:description" content="%(desc)s" />
<meta property="og:url" content="%(canonical)s" />
<meta property="og:image" content="%(og_image)s" />
<meta property="og:image:width" content="1200" />
<meta property="og:image:height" content="630" />
<meta property="og:locale" content="en_US" />
<meta name="twitter:card" content="summary_large_image" />
<meta name="twitter:title" content="%(title)s" />
<meta name="twitter:description" content="%(desc)s" />
<meta name="twitter:image" content="%(og_image)s" />
<!-- GENERATED by scripts/build_history_page.py from %(inst)s/metro-worksheet.json
     and the instance's own shipped data files. Do NOT hand-edit: `--check`
     fails the build. The stat tiles are MEASURED at generation time; the
     changelog entries are DATED snapshots and only ever appended (edit them
     in the worksheet's history_page.entries, newest first). -->
<script>
(function () {
  try {
    var stored = localStorage.getItem("districtry-theme");
    if (stored === "dark" || stored === "light") {
      document.documentElement.setAttribute("data-theme", stored);
    }
  } catch (e) { /* blocked storage — prefers-color-scheme decides */ }
})();
</script>
<style>
%(fontface)s

:root {
  color-scheme: light dark;
%(light)s
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
%(dark)s
  }
}
:root[data-theme="dark"] {
%(dark)s
}

* { box-sizing: border-box; }
body {
  margin: 0;
  background: var(--paper);
  color: var(--ink);
  font: 400 16px/1.6 var(--font-body);
  -webkit-text-size-adjust: 100%%;
}
a { color: var(--brand-700); }
main { max-width: 760px; margin: 0 auto; padding: 40px 20px 64px; }
.kicker {
  font: 600 13px/1 var(--font-body); letter-spacing: 0.08em;
  text-transform: uppercase; color: var(--muted); margin: 0 0 10px;
}
.kicker a { color: inherit; text-decoration: none; }
h1 { font: var(--font-heading-weight, 700) clamp(26px, 5vw, 34px)/1.15 var(--font-heading); margin: 0 0 12px; }
.intro { color: var(--ink-2); margin: 0 0 8px; }
.method {
  font-size: 14px; color: var(--muted); border-left: 3px solid var(--brand-border);
  padding: 2px 0 2px 12px; margin: 16px 0 0;
}
.tiles {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 12px; margin: 28px 0 8px;
}
.tile {
  border: 1px solid var(--border-soft, var(--border)); border-radius: var(--radius-card, 10px);
  padding: 14px 16px; background: var(--surface);
}
.tile-n { font: 700 28px/1.1 var(--font-heading); font-variant-numeric: tabular-nums; }
.tile-l { font-size: 13px; color: var(--ink-2); margin-top: 4px; }
.tile-s { font-size: 12px; color: var(--muted); margin-top: 4px; }
h2 {
  font: 700 20px/1.3 var(--font-heading);
  margin: 36px 0 6px; padding-top: 20px; border-top: 1px solid var(--border);
}
.timeline { list-style: none; margin: 12px 0 0; padding: 0; }
.entry { border-left: 3px solid var(--brand-border); padding: 0 0 4px 16px; margin: 0 0 22px; }
.entry-date {
  font: 600 12px/1 var(--font-body); letter-spacing: 0.06em; text-transform: uppercase;
  color: var(--brand-700); margin-bottom: 6px;
}
.entry h3 { font: 700 16px/1.35 var(--font-body); margin: 0 0 6px; }
.entry p { margin: 0; color: var(--ink-2); }
.jobs-scroll { overflow-x: auto; }
table { border-collapse: collapse; width: 100%%; margin-top: 12px; font-size: 14px; }
th, td { text-align: left; padding: 7px 12px 7px 0; border-bottom: 1px solid var(--border); vertical-align: top; }
th { font-size: 12px; letter-spacing: 0.05em; text-transform: uppercase; color: var(--muted); }
code { font: 400 12.5px/1.4 ui-monospace, "SF Mono", Menlo, Consolas, monospace; color: var(--ink-2); }
.foot { margin-top: 40px; padding-top: 16px; border-top: 1px solid var(--border); font-size: 14px; color: var(--muted); }
.foot a { margin-right: 14px; }
</style>
</head>
<body>
<main>
<p class="kicker"><svg class="districtry-mark" viewBox="0 0 96 96" width="18" height="18" aria-hidden="true" style="vertical-align:-3px;margin-right:6px"><g style="mix-blend-mode:multiply"><polygon points="51.5,63.2 12.4,55.7 11.5,18.6 42.7,5.0 72.7,35.3" fill="#6d3fd1" fill-opacity="0.55"></polygon></g><g style="mix-blend-mode:multiply"><polygon points="54.1,81.9 34.6,47.9 56.5,19.3 87.5,28.1 83.8,71.0" fill="#1d5fd6" fill-opacity="0.5"></polygon></g><g style="mix-blend-mode:multiply"><polygon points="13.7,64.5 27.6,31.2 62.7,37.6 70.3,66.9 33.9,89.0" fill="#b0316e" fill-opacity="0.45"></polygon></g><circle cx="42" cy="60" r="17" fill="none" stroke="#17161c" stroke-width="11"></circle><line x1="59" y1="16" x2="59" y2="82.5" stroke="#17161c" stroke-width="11"></line></svg><a href="./">districtry / %(metro_lower)s</a></p>
<h1>How this deployment grew</h1>
<p class="intro">%(intro)s</p>
<p class="method">The numbers below are measured from the app's own shipped
data files every time anything changes — they cannot drift from what the map
actually serves. The changelog entries are dated snapshots: each was true on
its own date, and none is edited after the fact.</p>
%(tiles)s
<h2>The changelog</h2>
<ul class="timeline">
%(entries)s
</ul>
<h2>Checked on a schedule</h2>
<p class="intro">Every scheduled job lands its changes as a reviewed pull
request — data about real officeholders never ships without a person looking
at the diff.</p>
<div class="jobs-scroll"><table>
<thead><tr><th>What it refreshes</th><th>Job</th><th>When</th></tr></thead>
<tbody>
%(workflows)s
</tbody>
</table></div>
<p class="foot">
<a href="./">Back to the map</a>
<a href="./sources.html">Sources &amp; data layers</a>
<a href="./faq.html">Common questions</a>
<a href="../privacy.html">Privacy</a>
<a href="https://overberg.co/why/" target="_blank" rel="noopener">Why this exists</a>
</p>
%(byline)s
</main>
</body>
</html>
""" % {
        "byline": shared_footer_byline(),
        "title": esc(title), "desc": esc(desc), "canonical": esc(canonical),
        "app_name": esc(app_name), "og_image": esc(app_url + "og-image.png"),
        "favicon": favicon_uri, "inst": inst,
        "fontface": fontface,
        "light": token_css(LIGHT_TOKENS, light, ":root"),
        "dark": token_css(DARK_TOKENS, dark, '[data-theme="dark"]', DARK_EXTRA,
                          indent="    "),
        "metro_lower": esc(place.lower()),
        "intro": esc(cfg["intro"]),
        "tiles": stat_tiles(tiles),
        "entries": "\n".join(entries_html),
        "workflows": "\n".join(workflow_rows),
    }


def main():
    check = "--check" in sys.argv[1:]
    built, skipped, problems = [], [], []
    for inst, worksheet_rel in INSTANCES:
        w = load_worksheet(worksheet_rel)
        if w is None:
            continue
        if "history_page" not in w:
            orphan = os.path.join(REPO_ROOT, inst, "history.html")
            if os.path.exists(orphan):
                problems.append(
                    "%s/history.html exists but the worksheet carries no "
                    "history_page key — an orphaned page nothing regenerates. "
                    "Add the key or remove the file." % inst)
            else:
                skipped.append(inst)
            continue
        html = build_instance(inst, w)
        out = os.path.join(REPO_ROOT, inst, w["history_page"]["file"])
        index_path = os.path.join(REPO_ROOT, inst, "index.html")
        with open(index_path, encoding="utf-8") as f:
            if ('href="./%s"' % w["history_page"]["file"]) not in f.read():
                problems.append(
                    "%s/index.html does not link ./%s — a history page nothing "
                    "points at is a page nobody reads"
                    % (inst, w["history_page"]["file"]))
        if check:
            current = ""
            if os.path.exists(out):
                with open(out, encoding="utf-8") as f:
                    current = f.read()
            if current != html:
                problems.append(
                    "%s is stale — regenerate with `python3 "
                    "scripts/build_history_page.py`" % os.path.relpath(out, REPO_ROOT))
            else:
                built.append(inst)
        else:
            with open(out, "w", encoding="utf-8") as f:
                f.write(html)
            built.append(inst)

    if problems:
        for p in problems:
            print("build-history-page: FAIL — %s" % p, file=sys.stderr)
        raise SystemExit(1)
    print("build-history-page: OK — %s"
          % "; ".join(filter(None, [
              "%d page(s) %s (%s)" % (len(built),
                                      "current" if check else "written",
                                      ", ".join(built)) if built else None,
              "opted out: %s" % ", ".join(skipped) if skipped else None])))


if __name__ == "__main__":
    main()
