#!/usr/bin/env bash
# C line-coverage gate for cfg._c (gcov).
#
# Builds the extension with coverage instrumentation + the PY_CFG_TESTING
# fault-injection hooks, runs the full test suite, produces the gcov report
# for src/conditional_method/_c.c and fails if the line coverage is below the
# threshold.
#
# Import-time-only functions (PyInit__c, CfgCallable_new_wrapper) are
# excluded from the accounting: their CFG_ALLOC_FAIL_GUARD branches fire only
# during module import, when the PY_CFG_TESTING fail counter is not armed, so
# they are unreachable by any test.  Counting them would punish every feature
# that adds import-time state (e.g. a new cache) with permanently-uncovered
# lines.  The gate measures genuinely testable coverage.
#
# Usage: scripts/coverage-gate.sh [threshold]   (default threshold: 90.0)
set -euo pipefail

cd "$(dirname "$0")/.."

THRESHOLD="${1:-90.0}"

# 1. Clean stale build artifacts and rebuild with coverage + fault injection.
#    `build/` must go entirely: setuptools treats build/lib/.../*.so newer than
#    the source as "up to date" and would skip recompiling, leaving no .gcno.
rm -f src/conditional_method/_c.abi3.so
rm -rf build

echo "==> Building cfg._c with --coverage + PY_CFG_TESTING"
CFLAGS="-DPY_CFG_TESTING --coverage -O0" LDFLAGS="--coverage" \
  uv run --group build python setup.py build_ext --inplace

# 2. Run the full test suite (generates the .gcda data files).
echo "==> Running test suite"
uv run --group test python -m pytest tests -q

# 3. Produce the gcov report for _c.c.
echo "==> Generating gcov report"
rm -f _c.c.gcov
GCOV_OUT=$(gcov -o build/temp.*/src/conditional_method src/conditional_method/_c.c 2>&1 || true)
echo "$GCOV_OUT" | grep -E "^File 'src/conditional_method/_c.c'|^Lines executed" || true

if [ ! -f _c.c.gcov ]; then
  echo "ERROR: gcov report _c.c.gcov not produced" >&2
  echo "$GCOV_OUT" >&2
  exit 1
fi

# 4. Compute testable coverage: take the last (authoritative) Lines-executed
#    total for _c.c from the gcov stdout, then drop import-time-only lines.
EXCLUDED_FUNCS="PyInit__c|CfgCallable_new_wrapper"
TOTAL=$(echo "$GCOV_OUT" | awk '
  /^File .*src\/conditional_method\/_c.c/ { want=1; next }
  want && /^Lines executed:[0-9.]+% of [0-9]+/ { total=$0 }
  END { if (total != "") { sub(/.*of /, "", total); print total } }
')
RESULT=$(python3 - "$TOTAL" "$EXCLUDED_FUNCS" <<'PYEOF'
import re
import sys

total = int(sys.argv[1])
excluded = sys.argv[2]
src_lines = open("src/conditional_method/_c.c").read().splitlines()
gcov_lines = open("_c.c.gcov").read().splitlines()


def enclosing(line_no: int) -> str:
    name = "?"
    for i, ln in enumerate(src_lines, 1):
        if i > line_no:
            break
        if ln.startswith(("static PyObject *", "static void ", "static int ", "PyMODINIT_FUNC")):
            name = ln[:70]
    return name


# Every gcov data row is an executable line: "<count>: <line>: <code>".
# Collect (src_line, uncovered_bool) for all executable rows.
executable = []  # (src_line, is_uncovered)
for ln in gcov_lines:
    m = re.match(r"\s*(\d+|#####):\s*(\d+):", ln)
    if not m:
        continue
    count, src_no = m.group(1), int(m.group(2))
    executable.append((src_no, count == "#####"))

excluded_total = sum(1 for s, _ in executable if re.search(excluded, enclosing(s)))
excluded_uncovered = sum(1 for s, u in executable if u and re.search(excluded, enclosing(s)))
uncovered_total = sum(1 for _, u in executable if u)

testable_total = total - excluded_total
testable_uncovered = uncovered_total - excluded_uncovered
testable_pct = (testable_total - testable_uncovered) / testable_total * 100.0
print(
    f"==> Testable coverage (excluded {excluded_uncovered} import-time "
    f"uncovered / {excluded_total} import-time executable lines): "
    f"{testable_pct:.2f}% of {testable_total}"
)
print(f"RESULT {testable_pct:.2f} {testable_total}")
PYEOF
)
echo "$RESULT" | grep "==>" || true
PCT=$(echo "$RESULT" | awk '/^RESULT/{print $2}')
TOTAL=$(echo "$RESULT" | awk '/^RESULT/{print $3}')

# 5. Gate: fail if coverage is below the threshold.
FAIL=0
awk -v pct="$PCT" -v thr="$THRESHOLD" -v total="$TOTAL" 'BEGIN {
  if (pct < thr) {
    printf "COVERAGE GATE FAILED: %.2f%% < %.2f%%\n", pct, thr;
    exit 1;
  }
  printf "COVERAGE GATE PASSED: %.2f%% (threshold %.2f%%, %s testable executable lines)\n",
    pct, thr, total;
  exit 0;
}' || FAIL=1

rm -f _c.c.gcov
exit $FAIL
