import json

import pytest

from mnemoreg import AlreadyRegisteredError, NotRegisteredError, Registry


def test_access_before_registration_raises() -> None:
    r: Registry[str, int] = Registry()
    with pytest.raises(NotRegisteredError):
        _ = r["missing"]


def test_reassign_same_key_is_not_allowed() -> None:
    r: Registry[str, int] = Registry()
    r["x"] = 1
    with pytest.raises(AlreadyRegisteredError):
        r["x"] = 2


def test_delete_twice_raises_cleanly() -> None:
    r: Registry[str, int] = Registry()
    r["a"] = 1
    del r["a"]
    with pytest.raises(NotRegisteredError):
        del r["a"]


def test_register_decorator_duplicate_key_fails() -> None:
    r: Registry[str, object] = Registry()

    @r.register("f")
    def f(x: int) -> int:
        return x

    with pytest.raises(AlreadyRegisteredError):

        @r.register("f")
        def g(y: int) -> int:
            return y


def test_register_with_non_string_key_type_hint_violation() -> None:
    r: Registry[str, int] = Registry()
    # Type hint violation—should still technically work but we test safety expectations
    r["1"] = 1
    with pytest.raises(TypeError):
        _ = r[1]  # using int instead of str


def test_get_returns_default_instead_of_raising() -> None:
    r: Registry[str, int] = Registry()
    assert r.get("unknown", 999) == 999
    assert r.get("unknown") is None


def test_to_json_fails_on_non_serializable_content() -> None:
    class Dummy:
        pass

    r: Registry[str, object] = Registry()
    r["obj"] = Dummy()
    with pytest.raises(TypeError):
        r.to_json()


def test_from_json_with_invalid_json_string() -> None:
    with pytest.raises(json.JSONDecodeError):
        Registry.from_json("{invalid}")


def test_snapshot_cannot_mutate_original_store_keys_directly() -> None:
    r: Registry[str, list[int]] = Registry()
    r["x"] = [1, 2, 3]
    snap = r.snapshot()
    snap["x"].append(4)  # same reference value
    assert r["x"] == [1, 2, 3, 4]
    # but removing a key in snapshot has no effect on registry
    del snap["x"]
    assert "x" in r


def test_bulk_context_does_not_swallow_exceptions() -> None:
    r: Registry[str, int] = Registry()
    with pytest.raises(ValueError):
        with r.bulk():
            r["a"] = 1
            raise ValueError("force exit")
    # confirm lock released
    r["b"] = 2
    assert r["b"] == 2
