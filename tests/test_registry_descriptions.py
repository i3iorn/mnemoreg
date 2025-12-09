from typing import Callable, Mapping, Optional, Tuple, cast

from mnemoreg import Registry


def test_register_decorator_stores_description() -> None:
    r: Registry[str, Callable[[int], int]] = Registry()

    @r.register("f")
    def plus_one(x: int) -> int:
        return x + 1

    # attach description using public update API to avoid decorator signature ambiguity
    # in type checks
    r.update(
        cast(
            Mapping[str, Tuple[Optional[Callable[[int], int]], Optional[str]]],
            {"f": (r["f"], "adds one")},
        )
    )

    snap = r.snapshot()
    assert "f" in snap
    item = snap["f"]
    # StoredItem should expose value and description
    assert callable(item.value)
    assert item.value(3) == 4
    assert item.description == "adds one"


def test_from_dict_with_descriptions() -> None:
    r: Registry[str, int] = Registry()
    r.update(cast(Mapping[str, Tuple[Optional[int], Optional[str]]], {"a": (1, "one")}))
    assert r["a"] == 1
    snap = r.snapshot()
    assert snap["a"].description == "one"


def test_update_with_descriptions_and_setitem_no_description() -> None:
    r: Registry[str, int] = Registry()
    # update accepts Stored tuples
    r.update(cast(Mapping[str, Tuple[Optional[int], Optional[str]]], {"b": (2, "two")}))
    assert r["b"] == 2
    assert r.snapshot()["b"].description == "two"

    # normal mapping assignment does not attach a description
    r["c"] = 3
    assert r["c"] == 3
    assert r.snapshot()["c"].description is None
