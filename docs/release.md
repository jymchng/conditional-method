# Release

How `python-cfg` is released.

## Versioning

Versions come from git via `setuptools-scm` (`guess-next-dev` scheme), so
the version is always derived from tags:

```bash
git tag v0.2.0
git push origin v0.2.0
```

## Release pipeline

A tag push (`v*`) triggers the full release workflow:

1. **CI** — lint, tests on CPython 3.9–3.14, coverage gate (>90%),
   sanitizers. All must pass.
2. **Wheels** — cibuildwheel builds the full many-arch `cp39-abi3` matrix
   (Linux x86_64/aarch64/i686/ppc64le/s390x/armv7l, macOS arm64/x86_64,
   Windows AMD64/ARM64/x86). Artifacts are tag-checked and smoke-tested.
3. **Release** — sdist + all wheels are uploaded to PyPI via **trusted
   publishing** (no hard-coded tokens), and a GitHub Release is created
   with the artifacts attached.

## PyPI

- Project name: **`python-cfg`**
- Import module: **`cfg`**

## Manual release (fallback)

```bash
uv build            # sdist + wheel
uv publish          # requires PyPI credentials / trusted publisher
```
