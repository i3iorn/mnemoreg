[![CI and Publish](https://github.com/i3iorn/mnemoreg/actions/workflows/publish.yml/badge.svg)](https://github.com/i3iorn/mnemoreg/actions/workflows/publish.yml)
# mnemoreg

mnemoreg is a tiny, dependency-free, thread-safe registry mapping useful for registering
callables and other values by string keys. It's intentionally small and
suitable for embedding in other projects. It uses only the Python standard
library and aims to provide a predictable, easy-to-use interface for
shared, named objects.

## Table of Contents
- [Highlights](#highlights)
- [Installation](#installation)
- [Quick start](#quick-start)
- [API summary](#api-summary)
- [Thread-safety and testing notes](#thread-safety-and-testing-notes)
- [Serialization](#serialization)
- [Development and testing](#development-and-testing)
- [Contributing](#contributing)
- [Troubleshooting](#troubleshooting)
- [License](#license)

## Highlights
- Small, single-file registry implementation (see `mnemoreg/core.py`).
- Thread-safe operations using `threading.RLock` and explicit `bulk()` context.
- Decorator-based registration for callables.
- Snapshot and (de)serialization helpers.
- Configurable overwrite behaviour (forbid / allow / warn).

## Installation
Install from PyPI:

```bash
pip install mnemoreg
```

Or install from source:

```bash
git clone https://github.com/i3iorn/mnemoreg.git
cd mnemoreg
pip install .
```

## Quick start

```python
from mnemoreg import Registry

# Create a registry typed for string keys and int values
r = Registry[str, int]()
r["one"] = 1
print(r["one"])  # 1

# Register a callable under an explicit key
@r.register("plus")
def plus(x):
    return x + 1

print(r["plus"](4))  # 5

# Register using the function name as the key
@r.register()
def multiply(x, y):
    return x * y

print(r["multiply"](3, 4))  # 12

# Use the bulk context manager to perform multiple operations under the same lock
with r.bulk():
    r["a"] = 1
    r["b"] = 2

# Create a shallow snapshot
snap = r.snapshot()
print(snap)
```

See the `tests/` directory for many additional examples and edge cases.

## API summary
This is a concise summary — see `mnemoreg/core.py` docstrings for full details.

- `Registry(*, lock: Optional[RLock]=None, log_level: int=logging.WARNING, overwrite_policy: int=OverwritePolicy.FORBID)` — constructor.
- Mapping-like methods: `__getitem__`, `__setitem__`, `__delitem__`, `__iter__`, `__len__`, `__contains__`.
- `register(key: Optional[str] = None)` — decorator to register callables/objects.
- `get(key, default=None)`, `snapshot()`, `to_dict()`.
- `from_dict(mapping)`, `from_json(s)` — classmethods to build from serialized data.
- `to_json(**kwargs)` — serialize to JSON string.
- `bulk()` — context manager that acquires the registry lock for batched operations.
- `update(mapping)`, `clear()`, `unregister(key)`, `remove(key)`.

Exceptions raised:
- `AlreadyRegisteredError` — when a key must not already exist but does.
- `NotRegisteredError` — when accessing/deleting a key that does not exist.

Overwrite behaviour is controlled by `OverwritePolicy` enum (FORBID=0, ALLOW=1, WARN=2).

## Thread-safety and testing notes
mnemoreg is guarded by a `threading.RLock` for mutating operations. Iteration and
`snapshot()` return shallow copies to avoid exposing internal state to concurrent
mutation.

If you write tests that intentionally start background threads which raise
exceptions (for example, tests that exercise concurrency failure modes), pytest
will surface a `PytestUnhandledThreadExceptionWarning` for uncaught exceptions
in threads. To hide that specific warning only for the threaded test module,
add this module-level filter to `tests/test_registry_threaded.py`:

```python
# tests/test_registry_threaded.py
import pytest

# suppress only the thread-unhandled warning for this module
pytestmark = pytest.mark.filterwarnings(
    "ignore::pytest.PytestUnhandledThreadExceptionWarning"
)
```

For the `pytest-asyncio` deprecation warning shown by newer versions:
configure the default fixture loop scope in your pytest configuration. For
example, in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
asyncio_mode = "strict"
asyncio_default_fixture_loop_scope = "function"
```

This sets the asyncio fixture loop scope explicitly and avoids the
`PytestDeprecationWarning` about the unset `asyncio_default_fixture_loop_scope`.

## Serialization
The registry supports basic JSON-friendly (de)serialization via `to_dict`,
`from_dict`, `to_json`, and `from_json`. These operate on shallow copies of the
internal store, so custom objects will need their own serialization logic before
being stored if you need to persist them as JSON.

Example:

```python
r = Registry[str, int]()
r["one"] = 1
s = r.to_json()
new_r = Registry.from_json(s)
```

## Development and testing
Run tests with:

```bash
python -m pytest -vv
```

The test suite covers single-threaded and concurrent scenarios. If you see
spurious warnings from async fixtures or thread exceptions while developing,
use the options described above to configure pytest or narrow the warning
filters to the affected test modules.

## Contributing
Contributions are welcome. A suggested workflow:

1. Open an issue to discuss larger changes.
2. Branch from `main` (or `master`) for new work.
3. Add tests for new behaviour or bug fixes.
4. Run the test suite and make sure everything passes.
5. Create a pull request with a clear description of the changes.

Coding style: keep changes small and well-tested. Prefer plain stdlib
implementations unless there is a clear productivity win from a dependency.

## Troubleshooting
- AlreadyRegisteredError during concurrent writes: your test or production
  logic may be attempting to re-register a key; consider `OverwritePolicy.ALLOW`
  or adjust the test flow to avoid races.
- `PytestUnhandledThreadExceptionWarning`: see the module-level `pytestmark`
  example above to suppress the warning only in the threaded test module.
- `pytest-asyncio` deprecation warnings: set
  `asyncio_default_fixture_loop_scope` in pytest config as shown above.

If you hit something not covered here, please open an issue with a small
reproduction.

## License
mnemoreg is licensed under the MIT License — see the `LICENSE` file for
details.

---

Maintainers: i3iorn
