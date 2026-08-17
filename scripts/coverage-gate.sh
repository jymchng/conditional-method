#!/usr/bin/env bash
# C line-coverage gate for cfg._c (gcov).
#
# Builds the extension with coverage instrumentation + the PY_CFG_TESTING
# fault-injection hooks, runs the full test suite, produces the gcov report
# for src/conditional_method/_c.c and fails if the line coverage is below the threshold.
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

# 3. Produce the gcov report for _c.c. The per-file summary line is printed
#    to stdout right after "File 'src/conditional_method/_c.c'".
echo "==> Generating gcov report"
rm -f _c.c.gcov
GCOV_OUT=$(gcov -o build/temp.*/src/conditional_method src/conditional_method/_c.c 2>&1 || true)
echo "$GCOV_OUT" | grep -E "^File 'src/conditional_method/_c.c'|^Lines executed" || true

if [ ! -f _c.c.gcov ]; then
  echo "ERROR: gcov report _c.c.gcov not produced" >&2
  echo "$GCOV_OUT" >&2
  exit 1
fi

# 4. Parse "Lines executed:XX.XX% of NNN" that follows "File 'src/conditional_method/_c.c'".
#    gcov may emit the same source twice (a partial first pass then the
#    complete pass, the latter with the higher total); take the LAST
#    occurrence — the full pass with the authoritative line total.
SUMMARY=$(echo "$GCOV_OUT" | awk '
  /^File .*src\/conditional_method\/_c.c/ { want=1; next }
  want && /^Lines executed:[0-9.]+% of [0-9]+/ { summary=$0 }
  END { if (summary != "") print summary }
')
if [ -z "$SUMMARY" ]; then
  echo "ERROR: could not parse coverage summary for _c.c from gcov output" >&2
  echo "$GCOV_OUT" >&2
  exit 1
fi
echo "==> $SUMMARY"

PCT=$(echo "$SUMMARY" | sed -E 's/.*Lines executed:([0-9.]+)%.*/\1/')
TOTAL=$(echo "$SUMMARY" | sed -E 's/.*of ([0-9]+).*/\1/')

# 5. Gate: fail if coverage is below the threshold.
FAIL=0
awk -v pct="$PCT" -v thr="$THRESHOLD" -v total="$TOTAL" 'BEGIN {
  if (pct < thr) {
    printf "COVERAGE GATE FAILED: %.2f%% < %.2f%%\n", pct, thr;
    exit 1;
  }
  printf "COVERAGE GATE PASSED: %.2f%% (threshold %.2f%%, %s executable lines)\n",
    pct, thr, total;
  exit 0;
}' || FAIL=1

rm -f _c.c.gcov
exit $FAIL
