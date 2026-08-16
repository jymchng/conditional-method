# Quickstart

## Conditional method selection

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
print(worker.work())  # development

# Only ONE `work` survives on the class — it is "well-formed":
print(Worker.__dict__.keys())
# dict_keys(['__module__', '__qualname__', 'work', ...])
```

## Callable conditions

Conditions can be callables evaluated lazily per call:

```python
import os

from conditional_method import conditional_method


class DatabaseConnector:
    @cfg(condition=lambda f: os.environ.get("ENV") == "production")
    def connect(self, config):
        return "production connection"

    @cfg(condition=lambda f: os.environ.get("ENV") != "production")
    def connect(self, config):
        return "default connection"
```

## Conditional decorators with `@cfg_attr`

```python
import os

from conditional_method import cfg_attr

os.environ["FEATURE_FLAG"] = "enabled"


def log_calls(fn):
    def wrapper(*args, **kwargs):
        print(f"calling {fn.__name__}")
        return fn(*args, **kwargs)

    return wrapper


@cfg_attr(
    condition=os.environ.get("FEATURE_FLAG") == "enabled",
    decorators=[log_calls],
)
def experimental(value):
    return value * 2
```

## Global functions and classes

`@cfg` also works on module-level functions and on classes themselves:

```python
from conditional_method import conditional_method


@cfg(condition=True)
class Person:
    def greet(self):
        return "hi"
```

See [Usage](usage.md) and [API Reference](api.md) for the full surface.
