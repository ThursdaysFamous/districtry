#!/usr/bin/env bash
# Vendor Leaflet + MapLibre GL locally for the headless smoke tests.
#
# Why this exists: each instance's index.html loads Leaflet and MapLibre GL
# (the vector-basemap renderer) from cdnjs.cloudflare.com. In the Claude Code
# web/sandbox environment the browser (Playwright's Chromium) cannot reach that
# CDN — it does not use the agent HTTPS proxy, so every request resets
# (ERR_CONNECTION_RESET → "L is not defined" → the app never boots). curl *can*
# reach the CDN through the proxy, so we fetch both libraries here and let each
# instance's smoke_test.mjs serve them same-origin via page.route(). (The
# maplibre-gl-leaflet bridge needs no vendoring: it is committed same-origin at
# <instance>/vendor/, so the static server already serves it.) Production and GitHub Actions CI are unaffected:
# they hit the real CDN and never see these dirs (they are gitignored and absent
# unless this script has run).
#
# ONE SCRIPT, EVERY INSTANCE. Three byte-identical copies of this used to live
# in scripts/, ca/scripts/ and ny/scripts/ — genuinely non-redundant while the
# instances were separate REPOS, because each self-located into its own tree.
# They are one repo now, one SessionStart hook fires at the repo root, and only
# the root copy ever ran: a sandboxed sf or nyc smoke run would have hit exactly
# the boot timeout described below. The instance table is the whole difference.
#
# EACH VENDOR DIR IS THE ONE ITS OWN SMOKE TEST LOOKS IN — smoke_test.mjs
# resolves `dirname(import.meta.url)/vendor/leaflet`, so the third column below
# must stay `<that instance's scripts dir>/vendor/leaflet`.
#
# FAILURE POSTURE, and it is two different things:
#   * The CDN being unreachable is a NETWORK condition — warn, exit 0, and the
#     smoke test falls back to loading Leaflet from the CDN as it always has.
#   * An instance whose index.html is missing, or carries no Leaflet CDN URL, is
#     a REPO BUG — exit 1, loudly. That case used to print a soft note and exit
#     0, and it cost a real debugging session at R2.3: moving the app to il/
#     left this script reading the repo-root index.html, which is now the
#     redirect stub. It skipped silently, and the smoke test died 45 seconds
#     later with `page.waitForFunction: Timeout` — a symptom CLAUDE.md
#     explicitly tells you NOT to chase into app code. A guard that goes quiet
#     when its own configuration is wrong is worse than no guard.
set -u

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# id : app file (relative to repo root) : vendor dir (relative to repo root)
INSTANCES=(
  "il:il/index.html:scripts/vendor/leaflet"
  "ca:ca/index.html:ca/scripts/vendor/leaflet"
  "ny:ny/index.html:ny/scripts/vendor/leaflet"
  "wi:wi/index.html:wi/scripts/vendor/leaflet"
  "ia:ia/index.html:ia/scripts/vendor/leaflet"
  "in:in/index.html:in/scripts/vendor/leaflet"
  "mi:mi/index.html:mi/scripts/vendor/leaflet"
  "mn:mn/index.html:mn/scripts/vendor/leaflet"
  "nc:nc/index.html:nc/scripts/vendor/leaflet"
  "ky:ky/index.html:ky/scripts/vendor/leaflet"
  "ok:ok/index.html:ok/scripts/vendor/leaflet"
)

wanted=("$@")
if [ "${#wanted[@]}" -eq 0 ]; then
  for row in "${INSTANCES[@]}"; do wanted+=("${row%%:*}"); done
fi

fail() { echo "vendor_leaflet: $*" >&2; exit 1; }

for id in "${wanted[@]}"; do
  row=""
  for candidate in "${INSTANCES[@]}"; do
    if [ "${candidate%%:*}" = "$id" ]; then row="$candidate"; break; fi
  done
  if [ -z "$row" ]; then
    known=""
    for candidate in "${INSTANCES[@]}"; do known="$known ${candidate%%:*}"; done
    fail "unknown instance '$id' — known:$known"
  fi

  rest="${row#*:}"
  index="$repo_root/${rest%%:*}"
  out="$repo_root/${rest#*:}"

  [ -f "$index" ] || fail "$id: ${rest%%:*} does not exist"

  # Mirror the exact URLs the app requests, so the vendored copies can never
  # drift from the instance's pinned Leaflet / MapLibre versions. (The pattern
  # also matches the re-inline curl commands in index.html's CSS comments —
  # harmless: the extra .css fetches land beside the ones the tests serve.)
  mapfile -t urls < <(grep -oE 'https://cdnjs\.cloudflare\.com/[^"]*/(leaflet|maplibre-gl)[^"/]*\.(js|css)' "$index" | sort -u)
  if [ "${#urls[@]}" -eq 0 ]; then
    fail "$id: no Leaflet CDN URL in ${rest%%:*} — is that still the app file?"
  fi

  mkdir -p "$out"
  for url in "${urls[@]}"; do
    name="${url##*/}"   # leaflet.js / leaflet.css / maplibre-gl.min.js / …
    if curl -fsS --max-time 30 -o "$out/$name" "$url"; then
      echo "vendor_leaflet: $id — fetched $name ($(wc -c <"$out/$name") bytes)"
    else
      echo "vendor_leaflet: $id — could not fetch $url; smoke test will fall back to CDN." >&2
      rm -f "$out/$name"
    fi
  done
done

exit 0
