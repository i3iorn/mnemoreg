import json

import pytest

from mnemoreg import (
    AlreadyRegisteredError,
    NotRegisteredError,
    Registry,
)


def test_set_get_and_delete_basic_behavior():
    r = Registry[str, int]()
    r["a"] = 1
    assert r["a"] == 1
    assert "a" in r
    assert len(r) == 1

    # delete and ensure missing
    del r["a"]
    assert "a" not in r
    assert len(r) == 0
    with pytest.raises(NotRegisteredError):
        _ = r["a"]


def test_duplicate_set_raises():
    r = Registry[str, int]()
    r["x"] = 10
    with pytest.raises(AlreadyRegisteredError):
        r["x"] = 20


def test_delete_not_registered_raises():
    r = Registry[str, int]()
    with pytest.raises(NotRegisteredError):
        del r["nope"]


def test_register_decorator_and_duplicate_decorator():
    r = Registry[str, object]()

    @r.register("f")
    def plus_one(x):
        return x + 1

    assert callable(r["f"])
    assert r.get("f")(3) == 4

    # decorator duplicate should raise at decoration-time
    with pytest.raises(AlreadyRegisteredError):

        @r.register("f")
        def another(x):
            return x


def test_get_default_behavior():
    r = Registry[str, int]()
    assert r.get("missing", "default") == "default"
    assert r.get("missing") is None


def test_snapshot_and_to_dict_and_from_dict_are_shallow_and_independent():
    r = Registry[str, dict]()
    r["conf"] = {"a": 1}

    snap = r.snapshot()
    assert snap == {"conf": {"a": 1}}

    # mutate snapshot and ensure original isn't affected
    snap["conf"]["a"] = 999  # shallow change: underlying value is same reference
    assert r["conf"]["a"] == 999  # values are same reference (shallow copy)
    # but replacing mapping in snapshot doesn't change original
    d = r.to_dict()
    d["conf"] = {"a": 0}
    assert r["conf"]["a"] == 999

    new = Registry.from_dict({"conf": {"a": 2}})
    assert new["conf"]["a"] == 2


def test_to_json_and_from_json_roundtrip():
    r = Registry[str, int]()
    r["num"] = 42
    s = r.to_json()
    # ensure it's valid JSON and roundtrips
    obj = json.loads(s)
    assert obj == {"num": 42}

    new = Registry.from_json(s)
    assert new["num"] == 42


def test_iter_returns_snapshot_iterator():
    r = Registry[str, int]()
    r["k1"] = 1
    it = iter(r)
    # mutate registry after getting iterator
    r["k2"] = 2
    # iterator was created from snapshot: should only contain k1
    items = list(it)
    assert items == ["k1"]
    # but iterating anew sees both
    assert list(iter(r)) == ["k1", "k2"]


def test_repr_contains_keys_and_len_and_contains_non_str_key():
    r = Registry[str, int]()
    r["one"] = 1
    r["two"] = 2
    rep = repr(r)
    assert "one" in rep and "two" in rep
    # __contains__ should accept any object (false for non-existing)
    assert (123 in r) is False


def test_bulk_context_manager_and_exception_propagation_releases_lock():
    r = Registry[str, int]()

    # normal usage should allow modifications while holding lock
    with r.bulk() as reg:
        # we are inside the context, it's the same object
        assert reg is r
        reg["a"] = 1
        assert r["a"] == 1

    # exception inside must propagate (return False from __exit__)
    # and not leave lock acquired
    with pytest.raises(ValueError):
        with r.bulk() as reg:
            reg["b"] = 2
            raise ValueError("boom")

    # after the exception, we can re-enter bulk (meaning lock was released)
    with r.bulk() as reg2:
        reg2["c"] = 3
        assert r["c"] == 3
