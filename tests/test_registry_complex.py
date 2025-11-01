import pytest

from mnemoreg import AlreadyRegisteredError, Registry


# Complex class hierarchy
class Base:
    def greet(self):
        return "base"


class Derived(Base):
    def greet(self):
        return "derived"


class Another:
    def greet(self):
        return "another"


# Small helper functions to replace assigned lambdas (avoid E731)
def lam1(x):
    return x**2


def lam2(x):
    return x - 1


# replace short lambda used in snapshot test
def func1(x):
    return x * 3


# replace short lambda used in repr test
def func(x):
    return x * 2


def test_complex_registration_mix():
    r = Registry[str, object]()

    # Regular functions
    def foo(x):
        return x + 1

    def bar(y):
        return y * 2

    # Lambdas (now named functions)
    # lam1 = lambda x: x**2
    # lam2 = lambda x: x - 1

    # Already decorated function
    @r.register("foo_func")
    def foo_dec(x):
        return x * 10

    # Already decorated class
    @r.register("base_cls")
    class BaseDec:
        def val(self):
            return "b"

    # Register via item assignment
    r["bar_func"] = bar
    r["lam1"] = lam1
    r["lam2"] = lam2
    r["derived_cls"] = Derived
    r["another_cls"] = Another

    # Check that all callable types work
    assert r["foo_func"](3) == 30
    assert r["bar_func"](4) == 8
    assert r["lam1"](5) == 25
    assert r["lam2"](10) == 9

    # Classes
    base_inst = r["base_cls"]()
    derived_inst = r["derived_cls"]()
    another_inst = r["another_cls"]()

    assert base_inst.val() == "b"
    assert derived_inst.greet() == "derived"
    assert another_inst.greet() == "another"

    # Attempt duplicate registration should fail
    with pytest.raises(AlreadyRegisteredError):
        r["foo_func"] = foo

    with pytest.raises(AlreadyRegisteredError):

        @r.register("lam1")
        def dummy():
            pass


def test_bulk_context_with_complex_operations():
    r = Registry[str, object]()
    r["a"] = 1
    r["b"] = 2

    def d(x):
        return x + 100

    with r.bulk() as reg:
        reg["c"] = 3
        reg["d"] = d
        del reg["a"]
        # overwrite within bulk
        with pytest.raises(AlreadyRegisteredError):
            reg["b"] = 20
        assert "a" not in reg

    # Outside context, state persists
    assert "a" not in r
    assert r["b"] == 2
    assert r["c"] == 3
    assert r["d"](5) == 105


def test_snapshot_iterator_consistency_with_complex_objects():
    r = Registry[str, object]()
    r["func1"] = func1
    r["cls1"] = Derived
    r["val1"] = {"key": 123}

    def new_func(x):
        return x + 5

    it = iter(r)
    # mutate after creating iterator
    r["new_func"] = new_func
    snapshot_keys = list(it)
    # snapshot should not include new_func
    assert "new_func" not in snapshot_keys
    # Live view includes all keys
    assert set(r) == {"func1", "cls1", "val1", "new_func"}


def test_json_roundtrip_with_complex_objects():
    r = Registry[str, object]()
    # JSON-serializable objects only
    r["num"] = 10
    r["lst"] = [1, 2, 3]
    r["dict"] = {"a": "x"}

    json_str = r.to_json()
    loaded = Registry.from_json(json_str)

    assert loaded["num"] == 10
    assert loaded["lst"] == [1, 2, 3]
    assert loaded["dict"] == {"a": "x"}


def test_multiple_decorators_on_same_registry():
    r = Registry[str, object]()

    @r.register("f1")
    def f1(x):
        return x + 1

    @r.register("f2")
    def f2(x):
        return x * 2

    @r.register("f3")
    class C3:
        def val(self):
            return "hello"

    # Decorate again with a different registry instance
    r2 = Registry[str, object]()

    @r2.register("f1")
    def f1_other(x):
        return x - 1

    assert r["f1"](5) == 6
    assert r["f2"](3) == 6
    assert r["f3"]().val() == "hello"
    assert r2["f1"](5) == 4


def test_nested_bulk_contexts_with_complex_changes():
    r = Registry[str, object]()
    r["x"] = 1
    r["y"] = 2

    with r.bulk() as outer:
        with pytest.raises(AlreadyRegisteredError):
            outer["x"] = 10
        outer["z"] = 3

        with r.bulk() as inner:
            with pytest.raises(AlreadyRegisteredError):
                inner["y"] = 20
            inner["w"] = 4

    # Check all changes persisted
    assert r["x"] == 1
    assert r["y"] == 2
    assert r["z"] == 3
    assert r["w"] == 4


def test_registering_callable_objects():
    r = Registry[str, object]()

    class CallableObj:
        def __call__(self, x):
            return x + 10

    obj = CallableObj()
    r["callable"] = obj

    assert callable(r["callable"])
    assert r["callable"](5) == 15


def test_snapshot_shallow_copy_with_nested_mutables():
    r = Registry[str, object]()
    nested = {"a": [1, 2]}
    r["nested"] = nested

    snap = r.snapshot()
    snap["nested"]["a"].append(3)
    # underlying registry sees the mutation (shallow)
    assert r["nested"]["a"] == [1, 2, 3]
    # replacing top-level mapping in snapshot does not affect registry
    snap["nested"] = {"b": 9}
    assert r["nested"] != {"b": 9}


def test_repr_and_contains_with_complex_keys_and_values():
    r = Registry[str, object]()
    r["cls"] = Derived
    r["func"] = func
    r["val"] = 42

    rep = repr(r)
    assert "cls" in rep
    assert "func" in rep
    assert "val" in rep

    # __contains__ works for existing and non-existing keys
    assert "cls" in r
    assert "func" in r
    assert "nonexistent" not in r
