from threading import RLock

import pytest

from mnemoreg import Registry
from mnemoreg.core import logger


def test_minimal_init():
    r = Registry()
    assert len(r) == 0
    assert isinstance(r.snapshot(), dict)
    assert r.to_dict() == {}
    assert r.to_json() == "{}"
    assert set(r) == set()


def test_init_with_lock():
    lock = RLock()
    r = Registry(lock=lock)
    assert r._lock is lock


def test_init_with_overwrite_policy():
    r = Registry(overwrite_policy=1)
    r["a"] = 1
    r["a"] = 2  # Should overwrite without error
    assert r["a"] == 2

    r2 = Registry(overwrite_policy=0)
    r2["b"] = 1
    with pytest.raises(Exception):
        r2["b"] = 2


def test_init_with_log_level():
    r = Registry(log_level=10)  # DEBUG level
    assert r is not None
    assert logger.getEffectiveLevel() == 10


def test_init_with_all_params():
    lock = RLock()
    r = Registry(lock=lock, log_level=20, overwrite_policy=1)
    assert r._lock is lock
    assert logger.getEffectiveLevel() == 20
    r["x"] = 10
    r["x"] = 20  # Should overwrite without error
    assert r["x"] == 20


def test_init_with_invalid_overwrite_policy():
    with pytest.raises(ValueError):
        Registry(overwrite_policy=-1)


def test_init_with_invalid_log_level():
    with pytest.raises(ValueError):
        Registry(log_level=-1)


def test_init_with_invalid_lock():
    with pytest.raises(TypeError):
        Registry(lock="not_a_lock")
