import json

import pytest

from mnemoreg import Registry


def test_empty_registry_len_and_repr_are_consistent():
    r = Registry[str, int]()
    assert len(r) == 0
    assert "Registry" in repr(r)
    assert repr(r).endswith("([])")


def test_register_empty_string_key():
    r = Registry[str, int]()
    with pytest.raises(ValueError):
        r[""] = 123


def test_register_special_character_keys():
    r = Registry[str, str]()
    key = "@#$%^&*()"
    r[key] = "weird"
    assert key in r
    assert r[key] == "weird"


def test_register_none_value_and_json_serialization():
    r = Registry[str, object]()
    r["none"] = None
    s = r.to_json()
    assert json.loads(s) == {"none": None}
    new = Registry.from_json(s)
    assert "none" in new
    # TODO: Implement differentiation of set None value and not set value
    # assert new["none"] is None


def test_decorator_registers_lambda_and_preserves_reference():
    r = Registry[str, object]()

    # use a named function instead of assigning a lambda to a name (E731)
    def double(x):
        return x * 2

    func = double
    decorated = r.register("lambda")(func)
    assert r["lambda"] is func is decorated


def test_overwrite_during_bulk_isolated_to_context():
    r = Registry[str, int]()
    r["a"] = 1
    with r.bulk() as reg:
        # intentionally delete and re-add same key inside context
        del reg["a"]
        reg["a"] = 2
        assert reg["a"] == 2
    # after exiting, state should persist
    assert r["a"] == 2


def test_from_dict_with_nonempty_input_copies_safely():
    data = {"x": 10}
    r = Registry.from_dict(data)
    assert r["x"] == 10
    data["x"] = 99  # mutate source dict
    assert r["x"] == 10  # copy must be independent


def test_to_json_fails_with_non_serializable_value(monkeypatch):
    class Unserializable:
        pass

    r = Registry[str, object]()
    r["bad"] = Unserializable()
    with pytest.raises(TypeError):
        _ = r.to_json()


def test_iteration_snapshot_does_not_reflect_future_mutations():
    r = Registry[str, int]()
    r["a"] = 1
    it = iter(r)
    r["b"] = 2
    assert list(it) == ["a"]  # snapshot
    assert set(r) == {"a", "b"}  # live view


def test_bulk_context_lock_release_even_on_nested_error():
    r = Registry[str, int]()
    try:
        with r.bulk() as reg:
            reg["a"] = 1
            with r.bulk() as nested:  # nested acquire allowed by RLock
                nested["b"] = 2
                raise RuntimeError("nested fail")
    except RuntimeError:
        pass
    # confirm lock released and usable again
    with r.bulk() as reg2:
        reg2["c"] = 3
        assert reg2["c"] == 3
