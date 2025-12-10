from dataclasses import dataclass
from typing import Any, Generic, Iterator, Optional, cast

from mnemoreg._types import V


@dataclass
class StoredItem(Generic[V]):
    """Transparent wrapper for stored values returned by `snapshot()`.

    The wrapper stores a value in the `value` attribute but delegates
    attribute access and many common operations to the underlying value so
    code can treat a StoredItem like the wrapped object (e.g. a list and
    call .append on the StoredItem).
    """

    _value: Any
    _description: Optional[str] = None

    def __init__(self, value: Optional[V], description: Optional[str] = None) -> None:
        self._value = value
        self._description = description

    @property
    def value(self) -> Optional[V]:
        return cast(Optional[V], self._value)

    @property
    def description(self) -> Optional[str]:
        return self._description

    def __getattr__(self, name: str) -> Any:
        return getattr(self._value, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if (
            name in ("_value", "_description")
            or name.startswith("_")
            or name in type(self).__dict__
        ):
            object.__setattr__(self, name, value)
        else:
            try:
                setattr(self._value, name, value)
            except Exception:
                object.__setattr__(self, name, value)

    def __repr__(self) -> str:  # pragma: no cover - trivial
        return (
            f"{self.__class__.__name__}("
            f"{self._value!r}, description={self._description!r})"
        )

    def __str__(self) -> str:
        return str(self._value)

    def __len__(self) -> int:
        return len(self._value)

    def __iter__(self) -> Iterator[Any]:
        return iter(self._value)

    def __getitem__(self, key: Any) -> Any:
        return self._value[key]

    def __setitem__(self, key: Any, val: Any) -> None:
        self._value[key] = val

    def __delitem__(self, key: Any) -> None:
        del self._value[key]

    def __contains__(self, item: Any) -> bool:
        return item in self._value

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        return self._value(*args, **kwargs)

    def __bool__(self) -> bool:
        return bool(self._value)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, StoredItem):
            return bool(self._value == other._value)
        return bool(self._value == other)
