#!/usr/bin/env bash
# ASan/UBSan gate for cfg._c.
#
# Builds the extension with AddressSanitizer + UndefinedBehaviorSanitizer
# (plus the PY_CFG_TESTING fault-injection hooks so the error paths are
# exercised), runs the full test suite under the sanitizer runtimes, and
# fails the build if any sanitizer report is emitted.
#
# CPython itself is not ASan-instrumented, so libasan is preloaded via
# LD_PRELOAD to initialize first; the extension links the sanitizer runtime.
#
# Usage: scripts/sanitize-gate.sh
set -euo pipefail

cd "$(dirname "$0")/.."

SAN_FLAGS="-fsanitize=address,undefined -fno-omit-frame-pointer -O1"

# 1. Clean stale artifacts and rebuild with the sanitizers + fault injection.
rm -f src/cfg/_c.abi3.so
rm -rf build

echo "==> Building cfg._c with ASan/UBSan + PY_CFG_TESTING"
CFLAGS="-DPY_CFG_TESTING ${SAN_FLAGS}" LDFLAGS="-fsanitize=address,undefined" \
  uv run --group build python setup.py build_ext --inplace

# 2. Locate libasan so it can be preloaded ahead of the interpreter.
LIBSAN=$(cc -print-file-name=libasan.so)
if [ ! -f "$LIBSAN" ]; then
  echo "ERROR: libasan not found (${LIBSAN})" >&2
  exit 1
fi
echo "==> libasan: $LIBSAN"

# 3. Run the full suite under the sanitizers.
#    - detect_leaks=0: LSan reports CPython's long-lived allocations as leaks.
#    - halt_on_error=1 (UBSan) / abort_on_error=1 (ASan): any report aborts
#      the interpreter, so pytest exits non-zero and the gate fails.
echo "==> Running test suite under ASan/UBSan"
export LD_PRELOAD="$LIBSAN"
export ASAN_OPTIONS="detect_leaks=0:abort_on_error=1:print_stacktrace=1"
export UBSAN_OPTIONS="print_stacktrace=1:halt_on_error=1"
export PYTHONMALLOC="malloc"

set +e
uv run --group test python -m pytest tests -q
STATUS=$?
set -e

echo "==> Sanitizer suite exit code: $STATUS"
if [ "$STATUS" -ne 0 ]; then
  echo "SANITIZER GATE FAILED: the test suite reported an ASan/UBSan error." >&2
  exit 1
fi
echo "SANITIZER GATE PASSED: no ASan/UBSan reports."
