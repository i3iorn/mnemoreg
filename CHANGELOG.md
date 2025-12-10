# Changelog

All notable changes to this project are documented in this file.

The format is loosely based on "Keep a Changelog":
https://keepachangelog.com/en/1.0.0/

## [Unreleased] - 2025-12-10

### Added
- Descriptions for stored values: entries may carry an optional human-readable
  description (string) alongside the stored value. Descriptions are stored as
  part of the internal storage representation and are exposed via the
  `Registry.snapshot()` API as `StoredItem.description`.
- Introduced a typed alias `Stored = Tuple[Optional[V], Optional[str]]` in
  `mnemoreg._types` to represent the (value, description) tuple consistently
  across the codebase.
- `Registry.register(...)` supports attaching a description when registering
  via the decorator (description available in snapshots).
- Storage protocol and backends updated:
  - `mnemoreg._storage.protocol.StorageProtocol` and
    `mnemoreg._storage.base.AbstractStorage` now use `Stored[V]` for get /
    to_dict / update signatures.
  - `MemoryStorage` (default backend) updated to store `Dict[K, Stored[V]]`.
- `Registry.from_dict` and `Registry.update` accept the Stored-form tuples so
  callers can persist/restore descriptions. `from_dict` has overloads to accept
  either plain value mappings or Stored-tuple mappings.
- `Registry.snapshot()` now returns a mapping of `StoredItem` wrappers which
  provide `.value` and `.description` properties; snapshot is a shallow copy
  (values are the same references).
- Added tests for description behavior: `tests/test_registry_descriptions.py`.

### Changed
- Many internal and public type annotations were tightened; tests were updated
  accordingly to satisfy strict `mypy` checks. This includes adding return
  type annotations to tests and using explicit generics where needed.
- `README.md` updated with examples and guidance on how descriptions work and
  how to persist them using the Stored tuple form.

### Fixed
- Resolved multiple `mypy` type errors across the project after introducing
  the description feature and the Stored alias.
- Updated tests and typing signatures so the test suite passes under strict
  mypy settings.

### Core refactor and API updates
- The `mnemoreg.core` implementation was refactored into a small package
  (`mnemoreg/core/`) with three focused modules: `registry.py`,
  `stored_item.py`, and `utils.py` to improve structure and testability.
- `Registry` now lives in `mnemoreg.core.registry` and includes these changes:
  - `register(..., description=...)`: decorator supports an optional
    description which is stored with the value and is exposed via
    `snapshot()`.
  - `snapshot()` returns `StoredItem` wrappers (defined in
    `stored_item.py`) exposing `.value` and `.description` while delegating
    common operations to the wrapped value.
  - `from_dict()` is overloaded to accept either a plain Mapping[K, V]
    or a Mapping[K, Stored[V]] (the internal (value, description) form) and
    will normalize input accordingly.
  - `update()` accepts either plain values or Stored-form tuples and will
    persist descriptions when provided.
  - `to_dict()` / `to_json()` remain intentionally value-centric (they
    return values only); to persist descriptions use the Stored form or the
    low-level store dump.
  - Lock validation tightened: provided `lock` objects are checked for
    context-manager and lock methods (enter/exit/acquire/release) to
    improve error messages when an invalid lock is supplied.
  - `bulk()` context manager remains available for batched operations and
    continues to rely on the guard lock (RLock by default).
- Storage typing: `StorageProtocol` and `AbstractStorage` signatures were
  updated to use the `Stored[V]` alias; `MemoryStorage` stores
  `Dict[K, Stored[V]]`.
- Typing and tests: a wide sweep of typing improvements was applied across
  the codebase to satisfy strict `mypy` checks; tests were updated with
  explicit annotations and new tests added for description behavior.

### Notes / Migration
- Backwards compatibility: the Registry mapping-like behavior for storing and
  retrieving values remains the same for the common cases (e.g. `r['k'] = v`,
  `r['k']`). However:
  - Internally values are now stored together with an optional description.
  - `to_dict()` / `to_json()` intentionally return the *values* only (no
    descriptions). If you need to persist descriptions, use `Registry.from_dict`
    / `Registry.update` with the Stored tuple form (value, description) or use
    the low-level storage `.to_dict()` which returns the internal Stored
    representation.
- If you implement a custom storage backend, update it to conform to the
  revised `StorageProtocol` signatures (methods accept and return `Stored[V]`).

## Previous releases
- See tags (if any) in the repository for prior release notes.

---

*Generated on 2025-12-10.*
