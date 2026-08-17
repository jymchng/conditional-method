# Installation

## Requirements

- CPython **3.9 – 3.14** (any one of them — a single abi3 wheel covers them
  all).

## Install from PyPI

```bash
pip install conditional-method
```

## Install from source

```bash
git clone https://github.com/jymchng/conditional-method.git
cd conditional-method
uv sync --group dev --group test --group build
uv run python setup.py build_ext --inplace
```

## Verify

```python
import conditional_method

print(conditional_method.__version__)  # e.g. 0.2.0.dev45
```

## Wheels

`conditional-method` is a C extension built against the Python Limited API (abi3).
One wheel per platform/architecture is published on PyPI with the tag
`cp39-abi3`, meaning it installs and runs on **every** CPython 3.9+ release
of that platform — no per-version rebuilds:

| Platform            | Architectures                                    |
| ------------------- | ------------------------------------------------ |
| Linux (manylinux)   | x86_64, aarch64, i686, ppc64le, s390x, armv7l    |
| macOS               | arm64, x86_64                                    |
| Windows             | AMD64, ARM64, x86                                |
