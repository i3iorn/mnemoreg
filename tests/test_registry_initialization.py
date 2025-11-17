from threading import RLock
from typing import Any, cast

import pytest

from mnemoreg import Registry
from mnemoreg.core import logger


def test_minimal_init() -> None:
    r: Registry[str, object] = Registry()
    assert len(r) == 0
    assert isinstance(r.snapshot(), dict)
    assert r.to_dict() == {}
    assert r.to_json() == "{}"
    assert set(r) == set()


def test_init_with_lock() -> None:
    lock = RLock()
    r: Registry[str, object] = Registry(lock=lock)
    # mypy reasons about r._lock as RLock; runtime identity check is fine
    assert r._lock is lock


def test_init_with_overwrite_policy() -> None:
    r: Registry[str, object] = Registry(overwrite_policy=1)
    r["a"] = 1
    r["a"] = 2  # Should overwrite without error
    assert r["a"] == 2

    r2: Registry[str, object] = Registry(overwrite_policy=0)
    r2["b"] = 1
    with pytest.raises(Exception):
        r2["b"] = 2


def test_init_with_log_level() -> None:
    r: Registry[str, object] = Registry(log_level=10)  # DEBUG level
    assert r is not None
    assert logger.getEffectiveLevel() == 10


def test_init_with_all_params() -> None:
    lock = RLock()
    r: Registry[str, object] = Registry(lock=lock, log_level=20, overwrite_policy=1)
    assert r._lock is lock
    assert logger.getEffectiveLevel() == 20
    r["x"] = 10
    r["x"] = 20  # Should overwrite without error
    assert r["x"] == 20


def test_init_with_invalid_overwrite_policy() -> None:
    with pytest.raises(ValueError):
        Registry(overwrite_policy=-1)


def test_init_with_invalid_log_level() -> None:
    with pytest.raises(ValueError):
        Registry(log_level=-1)


def test_init_with_invalid_lock() -> None:
    # cast the wrong-type lock to Any to avoid mypy arg-type complaint; test
    # still asserts runtime TypeError is raised by Registry
    with pytest.raises(TypeError):
        Registry(lock=cast(Any, "not_a_lock"))

    class FakeLock:
        def release(self) -> None:
            pass

        def __enter__(self) -> "FakeLock":
            return self

        def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
            pass

    lock = FakeLock()

    with pytest.raises(TypeError):
        Registry(lock=cast(Any, lock))


def test_init_with_rlock_like_object() -> None:
    class RLockLike:
        def acquire(self) -> None:
            pass

        def release(self) -> None:
            pass

        def __enter__(self) -> "RLockLike":
            return self

        def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
            pass

    lock = RLockLike()

    # Registry accepts lock-like objects at runtime; cast to Any for mypy
    r: Registry[str, object] = Registry(lock=cast(Any, lock))
    # Avoid mypy complaining about non-overlapping identity types by casting
    assert cast(Any, r._lock) is lock
