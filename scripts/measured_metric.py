#!/usr/bin/env python3
"""The measured-metric vocabulary, read by more than one gate.

WHY THIS IS A MODULE AND NOT A SECOND COPY. `build_history_page.py` invented
this grammar so a stat tile could not drift from the file it counts, and
`validate_gap_counts.py` needs exactly the same question answered about a
number written into a gap record's prose. Two readers of one question is where
this fleet's recurring defect starts — the privacy page and the analytics gate,
the steward mirror and the workflow, the chair record and its roster — so the
grammar and its evaluator live here and both callers import them.

WHAT MOVED AND WHAT DID NOT. This is `build_history_page.py`'s code, lifted
unchanged except that the two things it used to read off its own module —
the repository root and its `fail` — are now arguments. The history page
passes its own, so its failures still say `build-history-page`, and the proof
the lift was faithful is that all twelve history pages come back byte-identical.

THE VOCABULARY IS DELIBERATELY TINY and should stay that way: `keys`,
`features`, `sum:<field>`, `count-nonzero:<field>`, `people:<fields>` and
`keys-naming:<fields>`. Anything a caller cannot say in it is a number that
wants measuring by a purpose-built check rather than a grammar that grows to
fit one claim.
"""
import json
import os
import re


METRIC_RE = re.compile(
    r"^(keys|features|sum:[A-Za-z]+|count-nonzero:[A-Za-z]+"
    r"|people:[A-Za-z]+(?:\+[A-Za-z]+)*|keys-naming:[A-Za-z]+(?:\+[A-Za-z]+)*)$")

# A label using one of these is claiming something about PEOPLE, which is what
# makes a `keys` metric under it worth checking. The word list only decides
# WHETHER TO CHECK; it never decides the answer. That distinction is the
# correction of this gate's own first draft, which failed two ILGA tiles —
# "118 Illinois House seats with their member, party and both offices" — that
# are true: one key per seat, every key naming a member. A word cannot tell a
# true claim from a false one, so the check below measures instead.
# A label using one of these is claiming something about PEOPLE, which is what
# makes a `keys` metric under it worth checking. The word list only decides
# WHETHER TO CHECK; it never decides the answer. That distinction is the
# correction of this gate's own first draft, which failed two ILGA tiles —
# "118 Illinois House seats with their member, party and both offices" — that
# are true: one key per seat, every key naming a member. A word cannot tell a
# true claim from a false one, so the check below measures instead.
PERSON_WORDS = ("named", "seats", "officials", "members", "supervisors",
                "officeholders", "officers")


def people_in(record, fields):
    """People named on one record, under the fields the metric names.

    Three shapes, all of them in the shipped rosters: a bare name (Wisconsin's
    district records), an object with a `name` (a municipality's `head`), and a
    list of objects (a village board, Menominee's two countywide supervisors).
    Nothing outside the named fields is looked at, which is the whole point —
    `name` on a Wisconsin record is a supervisor and on an Illinois municipal
    record is the village.
    """
    found = 0
    for field in fields:
        value = record.get(field)
        if isinstance(value, str) and value.strip():
            found += 1
        elif isinstance(value, dict) and (value.get("name") or "").strip():
            found += 1
        elif isinstance(value, list):
            found += sum(1 for item in value
                         if isinstance(item, dict) and (item.get("name") or "").strip())
    return found


def measure_metric(root, inst, spec, fail):
    path = os.path.join(root, inst, spec["file"])
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
        label = spec["label"].lower()
        claimed = [w for w in PERSON_WORDS if w in label]
        if claimed:
            # A label about people, on a count of records. Whether that is false
            # is MEASURED, not reasoned: the tile declares where its people are
            # and this compares the keys against the keys that name somebody.
            # Equal, and one key is one named seat and `keys` is exactly right.
            # Unequal, and the tile is publishing a number for a different
            # quantity than its own words.
            naming = spec.get("naming")
            if not naming:
                fail("%s: metric %r counts KEYS and its label says %r, so it "
                     "needs a \"naming\" key giving the field(s) its people are "
                     "in, joined by +. Nothing can infer that: `name` on a "
                     "Wisconsin board record is a supervisor and on an Illinois "
                     "municipal record is the village."
                     % (inst, spec["label"], claimed[0]))
            fields = naming.split("+")
            counts = [people_in(v, fields) for v in data.values()
                      if isinstance(v, dict)]
            naming_keys = sum(1 for c in counts if c)
            if not naming_keys:
                fail("%s: metric %r declares naming=%r and no record in %s names "
                     "anybody under it" % (inst, spec["label"], naming, spec["file"]))
            if naming_keys != len(data):
                fail("%s: metric %r counts %d KEYS and its label says %r, but "
                     "only %d of those keys name anybody (naming=%s). Use "
                     "keys-naming:%s for the keys that do, or people:%s for "
                     "everyone named — %d of them."
                     % (inst, spec["label"], len(data), claimed[0], naming_keys,
                        naming, naming, naming, sum(counts)))
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
    if op in ("people", "keys-naming"):
        fields = field.split("+")
        counts = [people_in(v, fields) for v in data.values() if isinstance(v, dict)]
        if not any(counts):
            fail("%s: metric %r finds nobody in %s under %s — the fields named "
                 "are not where this file keeps its people"
                 % (inst, spec["label"], spec["file"], "+".join(fields)))
        return sum(counts) if op == "people" else sum(1 for c in counts if c)
    values = [v.get(field) for v in data.values() if isinstance(v, dict)]
    if op == "sum":
        return sum(v for v in values if isinstance(v, (int, float)))
    return sum(1 for v in values if v)
