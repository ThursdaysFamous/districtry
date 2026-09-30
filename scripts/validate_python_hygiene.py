#!/usr/bin/env python3
"""Three defects that ship green: a name bound nowhere, a dict key set twice,
and a shared module shadowing an instance's own copy of the same name.

WHY THIS EXISTS. On 2026-09-17 the municipal-officials refresh declined Logan
County's yearbook under robots.txt, exactly as it should, and then filed the
decline as an OUTAGE — "Municipal officials: Logan County source unavailable",
issue #983 — because the four lines that tell the workflow the reason was
compliance crashed on `name 'os' is not defined`. The scraper uses `os.environ`
to write `reason=robots` to GITHUB_OUTPUT and never imports `os`. The workflow's
own comment says what that costs: "Calling compliance an outage is how a robots
refusal gets 'fixed' by somebody later."

IT SHIPPED THROUGH AN 84-INVOCATION BATTERY AND FIVE DAYS OF WEEKLY RUNS,
because the line only executes when a host declines. A branch nothing takes is a
branch nothing tests, and this repo has 499 Python files full of them: every
per-county failure path, every floor, every refusal message.

THE DUPLICATE-KEY HALF IS THE SAME DEFECT IN A DIFFERENT LANGUAGE. On 2026-09-16
three weekly workflows went dead because a `run:` key appeared twice in one YAML
mapping (#978). PyYAML's safe_load keeps the LAST duplicate and every ordinary
read succeeded, which is why it reached main. PYTHON DOES THE SAME THING: a dict
literal with a key twice keeps the last value silently, and both instances found
on introduction were a considered edit being overwritten by the row it replaced —
scripts/build_county_outline.py had two "knox" anchor blocks, and
wi/scripts/build_wi_county_board_directory.py two "55039" rows whose urls differ.

THE THIRD IS THE ONLY ONE OF THE THREE THAT DOES NOT RAISE AT ALL. On
2026-09-30 two gap-outline builders were given the root scripts/ on their path
so they could read the shared robots seam, by inserting it at position 0. That
directory holds its own build_metro_outline.py — Illinois's — and so does each
instance's, with that state's own STATE_FIPS and county list, so the insert put
Illinois's copy first. Michigan's builder then ran to completion against
Illinois's counties and reported the state fabric as missing five county codes:
not an ImportError a reader could not miss, but a wrong answer with a plausible
message. The check fires only where a name is genuinely available from both
directories, so it says nothing about the thirty-odd files that add the shared
path and import nothing that can collide.

WHAT IT DELIBERATELY DOES NOT DO IS LINT. pyflakes finds both of these and 71
other things on this tree — unused imports, unused locals — and none of those
change what the code does. A gate whose output is mostly noise is one people
learn to skim, which is how the signal in it goes unread. These two classes were
chosen because each one was a live defect, in this repo, in the same week.

WHY STDLIB RATHER THAN pyflakes. scripts/requirements.txt is the SCRAPER pin
list, each entry carrying the parser or projection it exists for; a CI linter is
not a scraper dependency and does not belong on it. The check here is also
deliberately NARROWER than a linter's: it asks only whether a name is bound
NOWHERE in the file, collecting every binding form into one flat set rather than
modelling scopes. That over-approximates what is in scope at any given line,
which is the safe direction — it cannot report a name that some enclosing scope
really does provide, and it still catches the whole class the Logan bug is in.

ITS BLIND SPOTS ARE NAMED RATHER THAN IMPLIED. A file that does `from x import *`
or calls `exec`/`eval` can bind names this reader cannot see, so the name check
SKIPS such a file and the run prints it. Names injected by a caller or by a
conditional import inside a `try` are bound somewhere in the file and pass.
And a duplicate key whose two values are IDENTICAL is not reported: that is a
typo with no consequence, and reporting it would make the gate argue about
formatting.

Usage:
    python3 scripts/validate_python_hygiene.py            # the gate
    python3 scripts/validate_python_hygiene.py --selftest # proves it catches both
"""

import ast
import builtins
import contextlib
import io
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv"}

BUILTIN_NAMES = set(dir(builtins)) | {
    "__file__", "__name__", "__doc__", "__spec__", "__package__",
    "__loader__", "__builtins__", "__debug__",
}


class Bindings(ast.NodeVisitor):
    """Every name this module binds anywhere, and whether it binds names dynamically.

    Scopes are deliberately FLATTENED. The question asked is not "is this name in
    scope at this line" — that needs real scope analysis and gets subtle around
    comprehensions, class bodies and nonlocals — but "does this file bind this
    name at all". A name bound in any scope is treated as bound, which can only
    make the check quieter, never louder.
    """

    def __init__(self):
        self.names = set()
        self.dynamic = None          # the construct that hides bindings, if any

    def add(self, name):
        if name:
            self.names.add(name)

    def _args(self, args):
        for arg in list(args.posonlyargs) + list(args.args) + list(args.kwonlyargs):
            self.add(arg.arg)
        for arg in (args.vararg, args.kwarg):
            if arg:
                self.add(arg.arg)

    def visit_Import(self, node):
        for alias in node.names:
            self.add((alias.asname or alias.name).split(".")[0])

    def visit_ImportFrom(self, node):
        for alias in node.names:
            if alias.name == "*":
                self.dynamic = "from %s import *" % (node.module or "...")
            else:
                self.add(alias.asname or alias.name)

    def visit_FunctionDef(self, node):
        self.add(node.name)
        self._args(node.args)
        self.generic_visit(node)

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Lambda(self, node):
        self._args(node.args)
        self.generic_visit(node)

    def visit_ClassDef(self, node):
        self.add(node.name)
        self.generic_visit(node)

    def visit_Name(self, node):
        if isinstance(node.ctx, (ast.Store, ast.Del)):
            self.add(node.id)

    def visit_ExceptHandler(self, node):
        self.add(node.name)
        self.generic_visit(node)

    def visit_Global(self, node):
        for name in node.names:
            self.add(name)

    visit_Nonlocal = visit_Global

    def visit_MatchAs(self, node):
        self.add(node.name)
        self.generic_visit(node)

    def visit_MatchStar(self, node):
        self.add(node.name)
        self.generic_visit(node)

    def visit_MatchMapping(self, node):
        self.add(node.rest)
        self.generic_visit(node)

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name) and node.func.id in ("exec", "eval"):
            self.dynamic = "%s()" % node.func.id
        self.generic_visit(node)


def unbound_names(tree, bindings):
    """Names loaded by this module that it binds nowhere and Python does not provide."""
    found = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)
                and node.id not in bindings.names
                and node.id not in BUILTIN_NAMES):
            found.append((node.lineno, node.id))
    return found


def repeated_dict_keys(tree):
    """Constant keys set twice in one dict literal WITH DIFFERENT VALUES.

    Python keeps the last, so the earlier entry is dead code that reads exactly
    like live code — which is what makes it worth failing over rather than
    warning about.

    KEYS ARE COMPARED THE WAY PYTHON COMPARES THEM, by hash and equality of the
    values themselves. An earlier draft carried the type alongside each value, on
    the worry that `1` and `"1"` would be read as one key; they are not, because
    they are unequal. What that draft DID lose is the pair that genuinely
    collides — `{1: ..., True: ...}` is a one-entry dict — and its own self-test
    caught it.
    """
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue
        seen = {}
        for key, value in zip(node.keys, node.values):
            if not isinstance(key, ast.Constant):
                continue          # a computed key is not ours to reason about
            try:
                previous = seen.get(key.value)
            except TypeError:
                continue          # an unhashable constant is not a dict key
            if previous is not None:
                first_line, first_value = previous
                if ast.dump(first_value) != ast.dump(value):
                    found.append((key.lineno, key.value, first_line))
            seen[key.value] = (key.lineno, value)
    return found


def python_files(root):
    return sorted(p for p in pathlib.Path(root).rglob("*.py")
                  if not SKIP_DIRS & set(p.parts))


def shadowing_path_inserts(tree, own_modules, shared_modules):
    """[(lineno, module)] where a file puts the SHARED scripts/ dir ahead of its
    own on sys.path while importing a module name both directories hold.

    THE THIRD DEFECT THAT SHIPS GREEN, and the one that does not fail on the
    import. On 2026-09-30 two gap-outline builders needed the root scripts/ on
    the path for scraper_common, and got it with `sys.path.insert(0, ...)`. Each
    also imports build_metro_outline, which EXISTS IN BOTH DIRECTORIES — its own
    instance's, with that state's STATE_FIPS and county list, and the root's,
    which is Illinois's. Inserting at 0 put Illinois's copy first, so Michigan's
    builder ran to completion comparing Michigan's roster against Illinois's
    counties and reported the state fabric as missing five county codes. An
    ImportError would have been obvious; this was a wrong answer.

    So a file in that position must APPEND the shared directory, never insert
    it: an instance's own copy of a module has to win. The check is narrow on
    purpose — it fires only where a name is genuinely available from both
    places, so a file that merely inserts a path is not flagged, and neither is
    one whose imports cannot collide.
    """
    shared_inserts = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        if not (isinstance(fn, ast.Attribute) and fn.attr == "insert"
                and isinstance(fn.value, ast.Attribute) and fn.value.attr == "path"
                and isinstance(fn.value.value, ast.Name)
                and fn.value.value.id == "sys"):
            continue
        # `sys.path.insert(0, <something naming "scripts">)` is how this tree
        # spells "put the shared directory on the path". Any other index is not
        # ahead of the file's own directory, so it cannot shadow.
        if not (node.args and isinstance(node.args[0], ast.Constant)
                and node.args[0].value == 0):
            continue
        names_scripts = any(
            isinstance(x, ast.Constant) and x.value == "scripts"
            for x in ast.walk(node.args[1])) if len(node.args) > 1 else False
        if names_scripts:
            shared_inserts.append(node.lineno)
    if not shared_inserts:
        return []
    collidable = sorted(own_modules & shared_modules)
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            imported.add(node.module.split(".")[0])
        elif isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name.split(".")[0])
    hits = [m for m in collidable if m in imported]
    return [(lineno, m) for lineno in shared_inserts for m in hits]


def _modules_in(directory):
    try:
        return {f[:-3] for f in os.listdir(directory) if f.endswith(".py")}
    except OSError:
        return set()


def check_file(path, shared_modules=None):
    """(problems, skipped_reason) for one file."""
    source = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        return ["%s:%s: does not parse — %s" % (path, exc.lineno, exc.msg)], None

    bindings = Bindings()
    bindings.visit(tree)
    problems = []

    if bindings.dynamic is None:
        for lineno, name in unbound_names(tree, bindings):
            problems.append(
                "%s:%d: name %r is used and bound NOWHERE in this file — it will "
                "raise NameError the moment this line runs" % (path, lineno, name))
    if shared_modules is not None:
        own = _modules_in(path.parent)
        if str(path.parent.resolve()) != str((ROOT / "scripts").resolve()):
            for lineno, module in shadowing_path_inserts(tree, own, shared_modules):
                problems.append(
                    "%s:%d: this puts the shared scripts/ directory AHEAD of "
                    "this file's own on sys.path, and %r exists in both — so "
                    "the shared copy wins and this file silently runs another "
                    "instance's module. It does not fail on the import; it "
                    "returns a wrong answer. Append the shared directory "
                    "instead of inserting it at 0." % (path, lineno, module))
    for lineno, key, first_line in repeated_dict_keys(tree):
        problems.append(
            "%s:%d: dict key %r is set again here with a different value (first "
            "set at line %d) — Python keeps the LAST, so the earlier entry is "
            "dead" % (path, lineno, key, first_line))
    return problems, bindings.dynamic


def run(root=ROOT):
    files = python_files(root)
    if len(files) < 100:
        print("FAIL: only %d Python files found under %s — the tree this gate "
              "is meant to sweep has hundreds, so the walk is wrong"
              % (len(files), root), file=sys.stderr)
        return 1

    shared_modules = _modules_in(pathlib.Path(root) / "scripts")
    problems, skipped = [], []
    for path in files:
        found, dynamic = check_file(path, shared_modules)
        problems += found
        if dynamic:
            skipped.append((path.relative_to(root), dynamic))

    if skipped:
        print("NAME CHECK SKIPPED (%d file(s) bind names this reader cannot see):"
              % len(skipped))
        for rel, why in skipped:
            print("  %s — %s" % (rel, why))

    if problems:
        print("", file=sys.stderr)
        for line in problems:
            print("FAIL: %s" % line.replace(str(root) + "/", ""), file=sys.stderr)
        print("\n%d problem(s) in %d Python file(s)." % (len(problems), len(files)),
              file=sys.stderr)
        return 1

    print("OK - %d Python files: every loaded name is bound somewhere in its own "
          "file, no dict literal sets a key twice with different values, and no "
          "file shadows its own copy of a module with the shared scripts/ one "
          "(which holds %d module name(s))."
          % (len(files), len(shared_modules)))
    return 0


# ---------------------------------------------------------------------------
# Self-test. The gate reports ZERO on a clean tree, which is indistinguishable
# from a gate that looks at nothing -- the failure mode this repo has already
# paid for twice (a coverage check that printed "0 dispatched counties all
# inside the ring" as though that were a result). So the checks are driven
# against source that is known to carry each defect, and against source that
# carries its near-miss.
# ---------------------------------------------------------------------------

CASES = [
    # (label, source, expected number of problems)
    ("the Logan bug: os used, never imported",
     "def f():\n    return os.environ.get('X')\n", 1),
    ("the same file with the import",
     "import os\n\n\ndef f():\n    return os.environ.get('X')\n", 0),
    ("a name bound in another function still counts as bound",
     "def a():\n    global seen\n    seen = 1\n\n\ndef b():\n    return seen\n", 0),
    ("a comprehension target is a binding",
     "def f(rows):\n    return [r for r in rows if r]\n", 0),
    ("an except alias is a binding",
     "def f():\n    try:\n        pass\n    except ValueError as exc:\n"
     "        return exc\n", 0),
    ("a star import makes the name check unanswerable, so it is skipped",
     "from json import *\n\n\ndef f():\n    return dumps({})\n", 0),
    ("the knox shape: one key, two different values",
     "T = {\n    'knox': {'fips': '095', 'inside': [1]},\n"
     "    'macon': {'fips': '115'},\n    'knox': {'fips': '095', 'inside': [2]},\n}\n", 1),
    ("the same key twice with the SAME value is a typo, not a defect",
     "T = {\n    'a': 1,\n    'a': 1,\n}\n", 0),
    ("a computed key is not reasoned about",
     "K = 'a'\nT = {K: 1, K: 2}\n", 0),
    ("1 and True collide as dict keys and are reported",
     "T = {\n    1: 'one',\n    True: 'yes',\n}\n", 1),
    ("1 and '1' do not collide",
     "T = {\n    1: 'one',\n    '1': 'yes',\n}\n", 0),
]


def _selftest():
    import tempfile

    failures = 0
    with tempfile.TemporaryDirectory() as tmp:
        for i, (label, source, want) in enumerate(CASES):
            path = pathlib.Path(tmp) / ("case%d.py" % i)
            path.write_text(source, encoding="utf-8")
            problems, _ = check_file(path)
            ok = len(problems) == want
            failures += not ok
            print("  %-4s %s" % ("ok" if ok else "FAIL", label))
            if not ok:
                print("       wanted %d problem(s), got %d:" % (want, len(problems)))
                for line in problems:
                    print("         %s" % line)

    # The shadowing check needs two directories rather than one source string,
    # so it is driven against a real tree: an instance's own dir holding its own
    # copy of a shared module name, and a root scripts/ holding another.
    SHADOW_CASES = [
        ("insert(0, .../scripts) while importing a name both dirs hold", """\
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "scripts"))
from scraper_common import require_robots_once
from build_metro_outline import STATE_FIPS
""", 1),
        ("the same file appending instead", """\
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(HERE)), "scripts"))
from scraper_common import require_robots_once
from build_metro_outline import STATE_FIPS
""", 0),
        ("insert(0) but importing nothing that can collide", """\
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "scripts"))
from scraper_common import require_robots_once
""", 0),
        ("a non-zero index cannot get ahead of the file's own directory", """\
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(1, os.path.join(os.path.dirname(os.path.dirname(HERE)), "scripts"))
from build_metro_outline import STATE_FIPS
""", 0),
    ]
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        (root / "scripts").mkdir()
        (root / "scripts" / "scraper_common.py").write_text("", encoding="utf-8")
        (root / "scripts" / "build_metro_outline.py").write_text(
            "STATE_FIPS = '17'\n", encoding="utf-8")
        inst = root / "xx" / "scripts"
        inst.mkdir(parents=True)
        (inst / "build_metro_outline.py").write_text(
            "STATE_FIPS = '26'\n", encoding="utf-8")
        shared = _modules_in(root / "scripts")
        for i, (label, source, want) in enumerate(SHADOW_CASES):
            path = inst / ("shadow%d.py" % i)
            path.write_text(source, encoding="utf-8")
            problems, _ = check_file(path, shared)
            got = [x for x in problems if "AHEAD of" in x]
            ok = len(got) == want
            failures += not ok
            print("  %-4s %s" % ("ok" if ok else "FAIL", label))
            if not ok:
                print("       wanted %d, got %d: %s" % (want, len(got), got))

    # The walk itself: a directory with too few files must FAIL rather than
    # report a clean sweep of nothing.
    with tempfile.TemporaryDirectory() as tmp:
        (pathlib.Path(tmp) / "only.py").write_text("x = 1\n", encoding="utf-8")
        # Its FAIL line goes to stderr and is the point of the case, not a
        # failure of this run — swallowed so the self-test reads as one list.
        with contextlib.redirect_stderr(io.StringIO()):
            ok = run(pathlib.Path(tmp)) == 1
        failures += not ok
        print("  %-4s a tree too small to be this repo fails instead of passing"
              % ("ok" if ok else "FAIL"))

    if failures:
        print("\n%d self-test(s) failed." % failures, file=sys.stderr)
        return 1
    print("\nOK - all three checks behave on source that carries each defect and on "
          "source that carries its near-miss.")
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv[1:]:
        sys.exit(_selftest())
    sys.exit(run())
