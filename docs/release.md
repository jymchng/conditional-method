# Release

How `conditional-method` is released.

## Versioning

Versions come from git via `setuptools-scm` (`guess-next-dev` scheme), so
the version is always derived from tags:

```bash
git tag v0.2.0
git push origin v0.2.0
```

## Release pipeline

A tag push (`v*`) — or a manual `workflow_dispatch` with a tag — triggers
`.github/workflows/release.yml`:

1. **sdist** — `python -m build --sdist`; the version is verified against
   the tag (setuptools-scm).
2. **Wheels** — cibuildwheel builds the full many-arch `cp39-abi3` matrix
   (Linux x86_64/aarch64/i686/ppc64le/s390x/armv7l, macOS arm64/x86_64,
   Windows AMD64/ARM64/x86). Every wheel must carry the `cp39-abi3` tag.
3. **GitHub Release** — a draft release is created with the sdist + all
   wheels attached (SHA-256 integrity listing) and auto-generated notes.
4. **PyPI** — all artifacts are published to **`conditional-method`** via
   **trusted publishing** (OIDC, no hard-coded tokens), skipping
   already-uploaded files for idempotent re-runs.

Separately, every push runs CI (lint, tests on 3.9–3.14, coverage gate
>90%, ASan/UBSan) and the wheels/pages workflows — catch regressions
before you tag.

## Trusted publishing (one-time setup)

1. Register the project **`conditional-method`** on PyPI.
2. Add a publishing source: GitHub Actions, owner `jymchng`, repo
   `conditional-method`, workflow `release.yml`, environment `release`.
3. Done — the publish job authenticates via OIDC with no secrets.

## PyPI

- Project name: **`conditional-method`**
- Import module: **`conditional_method`** (legacy shim: `cfg`)

## Manual release (fallback)

```bash
uv build            # sdist + wheel
uv publish          # requires PyPI credentials / trusted publisher
```
