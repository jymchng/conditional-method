# Usage: `@cfg`

`@cfg` (aliases `@cm`, `@if_`) selects which of
several *identically named* method implementations survives on a class —
at **class build time**. Only the selected implementation remains in the
class's attribute set, so the class is *well-formed*: no runtime branching
inside method bodies, exactly one attribute per name.

## Forms

### 1. Decorator factory (recommended)

```python
from conditional_method import cfg


class Worker:
    @cfg(condition=ENV == "production")
    def work(self):
        return "production"

    @cfg(condition=ENV == "development")
    def work(self):
        return "development"
```

### 2. Direct application

```python
def work(self):
    return "production"


work = cfg(work, condition=True)
```

### 3. Without brackets

`@cfg` without brackets **raises `TypeError`** immediately (a condition is
required):

```python
@cfg  # TypeError: `@cfg` must be used as a decorator and
def work(self):  #   `condition` must be specified ...
    ...
```

## Conditions

A condition can be:

- a **bool** (or any truthy/falsy object) — evaluated once at decoration
  time;
- a **callable** taking the decorated function and returning a truthy value
  — evaluated lazily each time the implementation is selected.

```python
@cfg(condition=True)                      # static
@cfg(condition=lambda f: os.environ["X"])  # dynamic
```

## Selection rules

1. Each implementation is evaluated in source order.
2. The **last** implementation whose condition is true wins.
3. If **no** condition is true, the class build fails with
   `TypeError: None of the conditions is true for ...`.
4. If a condition callable raises `TypeError`, it is re-raised wrapped as
   `Error calling \`condition\` for <qualname>: ...`; other exceptions
   propagate unchanged.

## Where it works

- **Methods** — instance, `@classmethod`, `@staticmethod`, `@property`
- **Module-level functions**
- **Classes** themselves
- **Dunder methods** (`__enter__`, `__exit__`, `__new__`, ...)

## How it works

Each `@cfg` decorator evaluates its condition and either:

- **true** → caches the implementation under its qualified name
  (`module.Class.method`) and returns it unchanged, or
- **false** → returns a `TypeErrorRaiser` placeholder.

When the class body executes, the raiser's `__set_name__` fires: if a
condition was true for that qualname, the cached implementation replaces the
raiser; otherwise class creation fails. The cache is cleared strategically
to prevent leaks between unrelated names.
