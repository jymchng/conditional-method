#!/usr/bin/env python3
"""Re-tag a pyodide wheel from `pyemscripten_<abi>_wasm32` to `emscripten_<ver>_wasm32`.

micropip (bundled with pyodide) compares a wheel's platform tag via
`platform_to_version()` which strips only the `emscripten_` prefix (NOT
`pyemscripten_`). So a wheel tagged `pyemscripten_2025_0_wasm32` maps to
"pyemscripten.2025.0" and is REJECTED against a runtime built with Emscripten
"5.0.3", while `emscripten_5_0_3_wasm32` maps to "5.0.3" and is accepted.

pyodide-build 314 tags wheels `pyemscripten_<abi>_wasm32` (year-based ABI
version, e.g. 2025_0) even though the wheel is compiled with a real Emscripten
version (e.g. 5.0.3). The wheel binary is already compiled with the correct
Emscripten toolchain, so this script only rewrites the filename + `WHEEL`
metadata and recomputes `RECORD` (sha256 + size), leaving every other entry
byte-for-byte untouched. This is the exact transformation proven to install in
the AsyncMove playground (pyodide 314.0.3).

Usage:
    python scripts/retag_pyodide_wheel.py --emscripten-version 5.0.3 dist/*.whl
or  PYODIDE_EMSCRIPTEN_VERSION=5.0.3 python scripts/retag_pyodide_wheel.py dist/*.whl

Writes <name>-...-emscripten_<ver>_wasm32.whl next to each input wheel (a
no-op if the wheel already carries an `emscripten_*_wasm32` tag) and prints
the resulting filename.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import os
import re
import sys
import zipfile
from pathlib import Path

# Matches either pyemscripten_<abi>_wasm32 or emscripten_<ver>_wasm32 at the
# end of a wheel filename; captures the prefix (everything up to and including
# the last dash before the platform tag) and the existing platform version.
WHEEL_NAME_RE = re.compile(
    r"^(?P<rest>.*-)(?:py)?emscripten_(?P<ver>[a-zA-Z0-9_.]+)_wasm32\.whl$"
)
# Platform token inside e.g. the WHEEL file's `Tag:` line.
PLATFORM_TOKEN_RE = re.compile(r"(?:py)?emscripten_[a-zA-Z0-9_.]+_wasm32")


def retag(path: Path, emscripten_version: str) -> Path | None:
    m = WHEEL_NAME_RE.match(path.name)
    if not m:
        print(f"SKIP {path.name}: no (py)emscripten_*_wasm32 tag", file=sys.stderr)
        return None

    # Wheel platform tokens use underscores for the version (matching
    # pyodide-build's `platform()`: PYODIDE_EMSCRIPTEN_VERSION with dots
    # replaced by underscores), e.g. 5.0.3 -> emscripten_5_0_3_wasm32.
    platform_ver = emscripten_version.replace(".", "_")
    new_platform = f"emscripten_{platform_ver}_wasm32"
    if m.group("ver") == platform_ver:
        print(f"SKIP {path.name}: already tagged {new_platform}")
        return None

    out = path.with_name(f"{m.group('rest')}{new_platform}.whl")
    if out.exists() and out.resolve() == path.resolve():
        print(f"SKIP {path.name}: target {out.name} is the input itself")
        return None

    with zipfile.ZipFile(path) as zin:
        names = zin.namelist()
        wheel_meta = next((n for n in names if n.endswith("WHEEL")), None)
        record_meta = next((n for n in names if n.endswith("RECORD")), None)
        if wheel_meta is None:
            raise SystemExit(f"no WHEEL in {path.name}")

        wheel_data = zin.read(wheel_meta).decode()
        new_wheel_data = PLATFORM_TOKEN_RE.sub(new_platform, wheel_data)
        if new_wheel_data == wheel_data:
            print(
                f"WARN: no (py)emscripten platform token found in WHEEL for {path.name}",
                file=sys.stderr,
            )

        entries: list[tuple[str, bytes]] = []
        for info in zin.infolist():
            data = zin.read(info.filename)
            if info.filename == wheel_meta:
                data = new_wheel_data.encode()
            if info.filename == record_meta:
                continue  # recomputed below
            entries.append((info.filename, data))

        record_lines = []
        for name, data in entries:
            digest = base64.urlsafe_b64encode(
                hashlib.sha256(data).digest()
            ).rstrip(b"=").decode()
            record_lines.append(f"{name},sha256={digest},{len(data)}")
        record_data = ("\n".join(record_lines) + "\n" + f"{record_meta},,\n").encode()

        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zout:
            for name, data in entries:
                zout.writestr(name, data)
            zout.writestr(record_meta, record_data)

    print(out)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--emscripten-version",
        default=os.environ.get("PYODIDE_EMSCRIPTEN_VERSION", ""),
        help="Real Emscripten version of the build toolchain (e.g. 5.0.3). "
        "Defaults to $PYODIDE_EMSCRIPTEN_VERSION.",
    )
    parser.add_argument("wheels", nargs="+", help="pyodide wheel(s) to re-tag")
    args = parser.parse_args()

    if not args.emscripten_version:
        raise SystemExit(
            "--emscripten-version is required (or set $PYODIDE_EMSCRIPTEN_VERSION)"
        )
    if not re.fullmatch(r"[0-9][a-zA-Z0-9_.]*", args.emscripten_version):
        raise SystemExit(f"invalid Emscripten version: {args.emscripten_version!r}")

    for arg in args.wheels:
        retag(Path(arg), args.emscripten_version)


if __name__ == "__main__":
    main()
