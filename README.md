mnemoreg
========

A tiny, dependency-free, thread-safe registry mapping useful for registering
callables and values by string keys. Designed to be embedded in other projects
or used as a small standalone utility.

Key points
- Small, stdlib-only implementation.
- Thread-safe (uses RLock for mutations).
- Simple decorator-based registration for callables.

Quick facts
- Package exports: `Registry`, `AlreadyRegisteredError`, `NotRegisteredError`, `StorageProtocol`, and `__version__`.
- Main implementation: `mnemoreg/core.py`.
- Storage helpers live in `mnemoreg/_storage` (default in-memory backend is exported as `MemoeryStorage` — note: the name contains a historical typo).

Install
-------
From PyPI:

    pip install mnemoreg

From source (editable/development):

    git clone https://github.com/i3iorn/mnemoreg.git
    cd mnemoreg
    python -m venv .venv
    # Windows cmd.exe:
    .venv\Scripts\activate
    # PowerShell:
    .venv\Scripts\Activate.ps1
    # Unix/macOS:
    source .venv/bin/activate

    pip install -e .
    # dev extras:
    pip install -e .[dev]

Usage (quick)
-------------
The `Registry` behaves like a mapping from string keys to values. Examples:

```python
from mnemoreg import Registry, OverwritePolicy

r = Registry[str, int]()
r['one'] = 1
assert r['one'] == 1

# decorator registration (explicit key)
@r.register('plus')
def plus(x: int) -> int:
    return x + 1

assert r['plus'](4) == 5

# decorator registration (uses function.__name__ when key omitted)
@r.register()
def multiply(x: int, y: int) -> int:
    return x * y

assert r['multiply'](3, 4) == 12

# bulk operations (acquires the same lock for the block)
with r.bulk():
    r['a'] = 1
    r['b'] = 2

# removal
del r['a']  # there is no `unregister` helper; use deletion

# snapshots / serialization
snap = r.snapshot()      # shallow dict copy
s = r.to_json()          # JSON string (shallow)
new_r = Registry.from_json(s)
```

API / behavior summary
----------------------
- class Registry(Generic[K, V])
  - Mapping-like: `__getitem__`, `__setitem__`, `__delitem__`, `__iter__`, `__len__`, `__contains__`.
  - `register(key: Optional[str] = None)` — decorator to register functions/values.
  - `get(key, default=None)`, `snapshot()`, `to_dict()` — read helpers.
  - `from_dict(mapping)`, `from_json(s)` — classmethods to build a Registry from serialized data.
  - `to_json(**kwargs)` — serialize shallowly to JSON.
  - `bulk()` — context manager that acquires the registry lock for batched operations.
  - `update(mapping)`, `clear()`.

- Overwrite behavior: controlled by `OverwritePolicy` (FORBID = 0, ALLOW = 1, WARN = 2). The default is FORBID.

- Exceptions: `AlreadyRegisteredError`, `NotRegisteredError`.

Notes and caveats (important)
- The public API does not include `unregister()` or `remove()` — remove entries with `del registry[key]`.
- The storage package exports `MemoeryStorage` (typo). It's internal and only relevant when passing a custom `store=` to `Registry`.
- `Registry` expects string keys (type bound K=str) and will raise on invalid keys (empty, contains whitespace, or wrong type).

Development
-----------
This project uses pytest, ruff, black, isort, mypy, and pre-commit hooks.

Typical local developer setup:

```bash
python -m venv .venv
# activate the venv
pip install -e .[dev]
```

Run tests:

```bash
python -m pytest -q
```

Format / lint / checks (examples):

```bash
ruff check --fix .
isort --profile black .
black .
pre-commit run --all-files
python -m mypy mnemoreg --ignore-missing-imports
```

Pre-commit is configured in `.pre-commit-config.yaml`, and mypy/ruff settings live in `pyproject.toml`.

CI & publishing
----------------
There are GitHub Actions workflows under `.github/workflows/`.

The `publish.yml` workflow (current behavior):
- Triggers on: push to `main` or `master`, tag pushes matching `v*.*.*`, pull requests to `main`/`master`, and `workflow_dispatch`.
- The workflow runs tests, then attempts to determine/create a semver tag and push it, builds distributions, and (optionally) uploads to PyPI if the `MNEMOREG_PY_PI_TOKEN` secret is configured.

If you don't want to trigger the publish flow or accidental publishes:
- Work from a fork and open PRs from the fork — forks cannot push tags to the upstream repo and won't have the PyPI secret.
- Work on non-main branches; pushes to non-main branches do not trigger the `push` trigger (but PRs to `master` do trigger `pull_request`).
- Repository maintainers can tighten the workflow triggers (recommended): e.g. remove `pull_request` trigger, only run publish on explicit tag push or manual `workflow_dispatch`.
- Ensure `MNEMOREG_PY_PI_TOKEN` is never added unless you intend to publish.

Contributing
------------
Please follow the project's code style (black/ruff/isort) and add tests for new behavior.
Suggested flow for external contributors:
- Fork the repo.
- Create a feature branch in your fork and open a PR to `master`.
- Add tests and run the test suite locally.

License
-------
MIT — see the `LICENSE` file.

Maintainers
-----------
i3iorn
