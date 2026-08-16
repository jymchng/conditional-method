# conditional-method

`conditional-method` is a **zero-dependency, pure-C** Python library that lets you
select, at *class build time*, which of several identically-named method
implementations survives on a class — based on a runtime, startup, or
call-time condition.

```python
import os

from conditional_method import conditional_method

ENV = os.environ.get("ENV", "development")


class Worker:
    @cfg(condition=ENV == "production")
    def work(self, *args, **kwargs):
        return "production"

    @cfg(condition=ENV == "development")
    def work(self, *args, **kwargs):
        return "development"

    @cfg(condition=ENV == "staging")
    def work(self, *args, **kwargs):
        return "staging"


worker = Worker()
print(worker.work())  # development (only ONE `work` survives on Worker)
```

## Installation

```bash
pip install conditional-method
```

The whole implementation is a C extension (`conditional_method._c`) built against the
Python Limited API (abi3): a single `cp39-abi3` wheel covers CPython 3.9–3.14.

## What's here

- `@cfg` (aliases `@cm`, `@if_`) — conditional method
  selection at class build time.
- `@cfg_attr` — conditionally apply a chain of decorators.
- `debug` / `debug_enabled` — opt-in C debug logging.

## Why "well-formed" classes

Only the selected implementation remains in the class's attribute set, so the
resulting class is *well-formed*: there is exactly one `work` attribute, and
no runtime branching inside the method body.

See the [benchmarks](benchmarks.md) for measured performance.
