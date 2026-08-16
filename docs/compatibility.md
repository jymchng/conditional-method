# Compatibility

## Python versions

`conditional-method` supports **CPython 3.9 through 3.14**. Because the extension is
built against the **Limited API / stable ABI (abi3)**, a single `cp39-abi3`
wheel covers every CPython 3.9+ release — no per-version wheels are needed.

| Feature | 3.9 | 3.10 | 3.11 | 3.12 | 3.13 | 3.14 |
| --- | :-: | :-: | :-: | :-: | :-: | :-: |
| `@cfg` / `@cfg_attr` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| abi3 wheel | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Full test suite | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

## Known interpreter differences

Two CPython behaviors changed across the supported range; the test suite
handles both (`tests/_compat.py`):

1. **`__set_name__` error wrapping** — CPython < 3.12 wraps a `TypeError`
   raised by `__set_name__` in `RuntimeError: Error calling __set_name__
   on ...`; 3.12+ propagates the `TypeError` directly (with the wrapper
   text attached as a note). Your *code* is unaffected either way — a
   false `@cfg` method makes class creation fail — but if you catch these
   errors, match on both.

2. **Missing context-manager protocol** — using an object without
   `__enter__`/`__exit__` as a context manager raises `AttributeError` on
   < 3.11 and `TypeError` (`does not support the context manager protocol`)
   on 3.11+.

## Platforms

Wheels are published for:

- **Linux** (manylinux2_28 / musllinux): x86_64, aarch64, i686, ppc64le,
  s390x, armv7l
- **macOS**: arm64, x86_64
- **Windows**: AMD64, ARM64, x86

## Dependencies

`conditional-method` has **zero runtime dependencies**.
