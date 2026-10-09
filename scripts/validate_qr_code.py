#!/usr/bin/env python3
"""Hold the engine's QR block to an independent encoder, matrix for matrix.

WHAT IT GUARDS. `engine/index.html/qr-code.txt` turns a share permalink into a
QR code in the reader's browser. It is hand written because every QR image API
takes its payload in the URL of the image request, and our payload carries the
reader's selected point at full precision — today that point sits in the URL
FRAGMENT, which a browser never sends to a server, and a QR API would move it
into a query string, which is sent. So the choice is local code or a
transmission the privacy page cannot honestly describe. Local code it is, and a
hand-written encoder needs holding to something that is not itself.

This runs THE BLOCK AS SHIPPED — read from the engine file, evaluated in Node,
never re-implemented here — and compares its module matrix with `qrcode`'s.

THE REFERENCE IS `qrcode` AND NOT `segno`, AND THAT IS A MEASUREMENT RATHER
THAN A PREFERENCE. segno was tried first and disagreed with this block by 60
modules on a 21x21 symbol. Reading the codewords back out of both matrices, the
disagreement is one byte: where the spec's pad codewords are 0xEC then 0x11,
segno emits an extra 0x00 first. Its `write_padding_bits` does
`[0] * (8 - (length % 8))`, which appends a whole spurious zero byte when the
bit stream is ALREADY on a codeword boundary — and in byte mode it always is,
because 4 mode bits + 8 or 16 count bits + 8n data bits + a 4-bit terminator is
a multiple of 8 for every payload. `qrcode` agrees with this block exactly, and
the hand-derived codewords for "HELLO WORLD" at version 1 level M
(64, 180, 132, 84, 196, 196, 242, 5, 116, 245, 36, 196, 64, 236, 17, 236) agree
with both. segno's symbols still scan — a decoder reads the byte count from the
header and ignores what follows — so this is a conformance difference, not a
broken code, but it makes segno the wrong instrument for an exact comparison.

WHAT IS ASSERTED, AND THE ONE THING THAT IS ONLY BOUNDED.

  forced masks   Every one of the eight masks, at both levels, must produce a
                 byte-identical matrix. This is the correctness test: it covers
                 the codewords, the Reed-Solomon remainder, the block
                 interleaving, every function pattern, the format bits and the
                 data placement.

  chosen mask    ALLOWED TO DIFFER, and bounded rather than fixed. Any of the
                 eight masks yields a valid symbol; which one an encoder picks
                 is an optimisation scored by four penalty rules the standard
                 states in prose, and implementations read rule 3 differently —
                 this block counts a finder-like run once if either side has
                 four light modules, `qrcode` searches for two explicit
                 11-module patterns and so counts a run with light on both
                 sides twice. So the gate scores all eight of THIS BLOCK's
                 matrices with `qrcode`'s own scorer and requires the mask the
                 block picked to be within MASK_PENALTY_MAX of the best. It was
                 the best in 15 of 16 cases when this was written
                 (2026-09-27) and 50 worse in one, so a regression in the
                 penalty code shows up as a widening gap rather than passing
                 silently. The OK line prints the worst gap measured.

  refusal        A payload too long for version 40 must return null, so a
                 caller can say so rather than draw something that cannot be
                 read.

  svg            The SVG must carry exactly one filled rectangle per dark
                 module, so the drawing cannot drift from the matrix.

LEVELS L AND M ONLY, because nothing here needs Q or H: the longest share URL
an app can hand out measured 663 bytes on 2026-09-27 (all 40 Illinois layers
on, with a pin and the stats flag), which is version 18 at L and 20 at M. Links
have been written in a short form since 2026-10-09 (layer codes, one-letter
keys, `?ref=qr`), and the same worst case — now all 41 Illinois layers — then
measured 199 bytes, version 9 at L and 10 at M; the long-form cases below stay
because a longer payload is a harder test of the encoder, not a likelier one.

Usage:
  python3 scripts/validate_qr_code.py            # the CI gate
  python3 scripts/validate_qr_code.py --report   # every case
"""
import argparse
import json
import os
import random
import re
import subprocess
import sys

import qrcode
from qrcode.util import QRData, MODE_8BIT_BYTE, lost_point

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BLOCK = os.path.join(ROOT, "engine", "index.html", "qr-code.txt")

# The worst penalty this block's chosen mask may pay against the best of its own
# eight, scored by qrcode's scorer. Measured worst 50 on the cases below when the
# block was written; pinned rather than derived, because a ceiling recomputed
# from the run can never fail.
MASK_PENALTY_MAX = 120

LEVELS = {"L": qrcode.constants.ERROR_CORRECT_L, "M": qrcode.constants.ERROR_CORRECT_M}

NODE_DRIVER = r"""
const fs = require("fs");
const block = fs.readFileSync(process.argv[1], "utf8");
const m = new Function(block + "\nreturn { qrEncode, qrSvg };")();
const cases = JSON.parse(fs.readFileSync(0, "utf8"));
process.stdout.write(JSON.stringify(cases.map(function (c) {
  if (c.svg) {
    const s = m.qrSvg(c.text, { level: c.level });
    return s ? { svg: s.svg, version: s.version, size: s.size } : null;
  }
  const auto = m.qrEncode(c.text, { level: c.level });
  if (!auto) return null;
  const all = [];
  for (let k = 0; k < 8; k++) {
    all.push(m.qrEncode(c.text, { level: c.level, mask: k }).modules.map(function (row) {
      return row.map(function (v) { return v ? 1 : 0; });
    }));
  }
  return { version: auto.version, mask: auto.mask, all: all };
})));
"""


def cases():
    """Real share URLs, the measured longest one, and the awkward lengths."""
    random.seed(20260927)
    junk = lambda n: "".join(random.choice("abcdefghijklmnop0123456789-_/#=&,.")
                             for _ in range(n))
    il = "https://districtry.com/il/?utm_source=share&utm_medium=qr"
    wi = "https://districtry.com/wi/?utm_source=share&utm_medium=qr"
    return [
        il + "#point=41.88250,-87.62850",
        il + "#point=41.88250,-87.62850&zoom=14",
        il + "#point=41.88250,-87.62850&zoom=14&layers=ward,congress,county-board",
        il + "#point=41.88250,-87.62850&zoom=16&layers=ward,congress,il-house"
             "&pin=congress&stats=1",
        wi + "#point=43.07450,-89.38400&zoom=16&layers=county-board,wi-senate,"
             "wi-assembly,municipality,school-district-unified&pin=county-board&stats=1",
        "HELLO WORLD",
        "a", "y" * 7, "z" * 8, "q" * 9, "w" * 40,     # around the count-field and byte edges
        junk(120), junk(300), junk(663), junk(900),   # 663 was the longest share URL before 2026-10-09
        "café — Zürich #point=41.9,-87.6",  # multi-byte UTF-8
    ]


def run_node(payload):
    res = subprocess.run(["node", "-e", NODE_DRIVER, BLOCK], input=json.dumps(payload),
                         capture_output=True, text=True)
    if res.returncode != 0:
        raise SystemExit("validate-qr-code: FAIL — the block did not run in Node:\n"
                         + res.stderr[-2000:])
    return json.loads(res.stdout)


def reference(text, version, level, mask):
    q = qrcode.QRCode(version=version, error_correction=LEVELS[level],
                      border=0, mask_pattern=mask)
    q.add_data(QRData(text.encode("utf-8"), mode=MODE_8BIT_BYTE))
    q.make(fit=False)
    return [[1 if v else 0 for v in row] for row in q.get_matrix()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true", help="print every case")
    args = ap.parse_args()

    texts = cases()
    jobs = [{"text": t, "level": lv} for t in texts for lv in ("L", "M")]
    got = run_node(jobs)

    fails, compared, worst_gap, worst_case = [], 0, 0, None
    for job, out in zip(jobs, got):
        if out is None:
            fails.append("%s (%d bytes): the block refused a payload it should encode"
                         % (job["level"], len(job["text"].encode())))
            continue
        for mask in range(8):
            ref = reference(job["text"], out["version"], job["level"], mask)
            mine = out["all"][mask]
            compared += 1
            if ref != mine:
                n = sum(1 for r in range(len(ref)) for c in range(len(ref))
                        if ref[r][c] != mine[r][c])
                fails.append("v%d %s mask %d (%d bytes): %d module(s) differ from qrcode"
                             % (out["version"], job["level"], mask,
                                len(job["text"].encode()), n))
        scores = [lost_point([[bool(v) for v in row] for row in mm]) for mm in out["all"]]
        gap = scores[out["mask"]] - min(scores)
        if gap > worst_gap:
            worst_gap, worst_case = gap, "v%d %s (%d bytes)" % (
                out["version"], job["level"], len(job["text"].encode()))
        if gap > MASK_PENALTY_MAX:
            fails.append("v%d %s (%d bytes): chosen mask %d scores %d against the best %d "
                         "(+%d, ceiling %d) — the penalty rules have drifted"
                         % (out["version"], job["level"], len(job["text"].encode()),
                            out["mask"], scores[out["mask"]], min(scores), gap,
                            MASK_PENALTY_MAX))
        if args.report:
            print("  v%-2d %s %-5d bytes  mask %d  penalty gap %+d"
                  % (out["version"], job["level"], len(job["text"].encode()),
                     out["mask"], gap))

    # Refusal: past version 40 at level L (2,953 bytes) there is no symbol to draw.
    over = run_node([{"text": "x" * 4000, "level": "L"}])[0]
    if over is not None:
        fails.append("a 4,000-byte payload encoded, where version 40 at L holds 2,953 — "
                     "the block must return null so a caller can say so")

    # The drawing must carry one rectangle per dark module.
    svg_job = {"text": cases()[3], "level": "M", "svg": True}
    svg = run_node([svg_job])[0]
    if svg is None:
        fails.append("qrSvg returned nothing for a payload qrEncode accepts")
    else:
        enc = run_node([{"text": svg_job["text"], "level": "M"}])[0]
        dark = sum(sum(row) for row in enc["all"][enc["mask"]])
        drawn = len(re.findall(r"h1v1h-1z", svg["svg"]))
        if dark != drawn:
            fails.append("qrSvg drew %d rectangle(s) for %d dark module(s)" % (drawn, dark))

    if fails:
        print("validate-qr-code: FAIL")
        for f in fails:
            print("  " + f)
        return 1
    print("validate-qr-code: OK — %d matrix comparison(s) against qrcode, all identical; "
          "worst chosen-mask penalty gap %d of %d allowed (%s); refusal and SVG hold"
          % (compared, worst_gap, MASK_PENALTY_MAX, worst_case))
    return 0


if __name__ == "__main__":
    sys.exit(main())
