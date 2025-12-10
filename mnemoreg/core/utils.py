from enum import IntEnum
from typing import Any, Callable, cast

from mnemoreg import StorageProtocol
from mnemoreg._storage import MemoryStorage
from mnemoreg._types import K, V


def locked_method(method: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to lock method calls for thread safety."""
    from .registry import Registry

    def wrapper(self: "Registry[K, V]", *args: Any, **kwargs: Any) -> Any:
        with self._lock:
            return method(self, *args, **kwargs)

    return wrapper


def _make_default_store() -> StorageProtocol[K, V]:
    """Create a default StorageProtocol[K, V] instance.

    Construct the concrete MemoryStorage() at runtime and cast it to the
    protocol with generics so the module-level type inference remains
    precise. Localizes the unavoidable cast to one place.
    """
    return cast(StorageProtocol[K, V], MemoryStorage())


class OverwritePolicy(IntEnum):
    FORBID = 0
    ALLOW = 1
    WARN = 2
