# Security

## Reporting a vulnerability

If you discover a security issue in `conditional-method`, **please do not** open a
public issue. Report it privately via GitHub's
[security advisory workflow](https://github.com/jymchng/conditional-method/security/advisories/new)
or by emailing the maintainers.

Please include:

- a minimal reproduction,
- the affected version(s),
- the impact and any proposed fix.

## Security posture

- **Memory safety**: the C extension (`cfg._c`) is a memory-safety
  boundary. Refcount correctness, GC participation, and error-path
  discipline are enforced by code review, the ASan/UBSan CI job, and the
  allocation-failure injection test suite.
- **Zero runtime dependencies**: `conditional-method` has no third-party runtime
  dependencies, minimizing the supply-chain surface.
- **No secrets committed**: credentials are never stored in the repository;
  release automation uses environment secrets and trusted publishing.
- **Least privilege**: GitHub Actions workflows declare only the
  permissions they need.
- **Releases are protected**: publishing is gated on CI (lint, tests,
  coverage >90%, sanitizers) and uses PyPI trusted publishing.

## Supported versions

Security fixes are provided for the latest release. Older releases receive
fixes on a best-effort basis; upgrade to the newest `conditional-method` to stay
current.

## Reporting process

1. You report a vulnerability privately (advisory or email).
2. The maintainers acknowledge within 5 business days.
3. A fix is prepared, tested against the full CI matrix, and released.
4. The advisory is disclosed after the fix ships.
