"""Thread-safe Registry implementation.

This module provides a simple, well-tested `Registry` that implements
`collections.abc.MutableMapping` semantics with an internal `RLock` to
support concurrent access. It is intentionally small and explicit.
"""

import json
import logging
from threading import RLock
from typing import (
    Any,
    Callable,
    ContextManager,
    Dict,
    Generic,
    Iterator,
    Mapping,
    MutableMapping,
    Optional,
    TypeVar,
)

K = TypeVar("K", bound=str)
V = TypeVar("V")

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)


class RegistryError(Exception):
    pass


class AlreadyRegisteredError(RegistryError, KeyError):
    pass


class NotRegisteredError(RegistryError, KeyError):
    pass


class Registry(MutableMapping, Generic[K, V]):
    """
    Thread-safe registry implementing MutableMapping.

    Arguments:
        lock: Optional lock object to use for synchronization. If None,
            a new RLock is created for threadsafe operation.
    """

    def __init__(self, *, lock: Optional[RLock] = None) -> None:
        # _lock is an RLock (supports context manager, acquire/release)
        self._lock: RLock = lock or RLock()
        self._store: Dict[K, V] = {}

    # Mapping protocol
    def __getitem__(self, key: K) -> V:
        """Return value for `key` or raise NotRegisteredError."""
        with self._lock:
            try:
                return self._store[key]
            except KeyError:
                raise NotRegisteredError(f"Registry key {key!r} is not registered")

    def __setitem__(self, key: K, value: V) -> None:
        """Register a new key/value pair. Duplicate keys raise
        AlreadyRegisteredError.
        """
        # behave like add/register (reject duplicate)
        with self._lock:
            if key in self._store:
                raise AlreadyRegisteredError(
                    f"Registry key {key!r} is already registered"
                )
            self._store[key] = value
            logger.debug("Registered %s -> %s", key, type(value))

    def __delitem__(self, key: K) -> None:
        """Remove a key from the registry or raise NotRegisteredError if
        missing.
        """
        with self._lock:
            if key in self._store:
                del self._store[key]
                logger.debug("Unregistered %s", key)
            else:
                raise NotRegisteredError(f"Registry key {key!r} is not registered")

    def __iter__(self) -> Iterator[K]:
        """Return an iterator over a snapshot of the keys (safe to
        iterate without holding lock).
        """
        with self._lock:
            # return a snapshot iterator to avoid holding lock during
            # iteration
            return iter(list(self._store.keys()))

    def __len__(self) -> int:
        with self._lock:
            return len(self._store)

    def __contains__(self, key: object) -> bool:
        with self._lock:
            return key in self._store

    def __repr__(self) -> str:
        with self._lock:
            return f"{self.__class__.__name__}({list(self._store.keys())!r})"

    # Convenience APIs
    def register(self, key: Optional[K] = None) -> Callable[[V], V]:
        """Decorator to register an object under `key`.

        Returns the decorated object.
        Raises AlreadyRegisteredError if key exists.
        """

        def decorator(obj: V) -> V:
            reg_key = key if key is not None else getattr(obj, "__name__", None)
            if reg_key is None:
                raise ValueError(
                    "Registry key must be provided or object must have __name__"
                )
            with self._lock:
                if reg_key in self._store:
                    raise AlreadyRegisteredError(
                        f"Registry key {reg_key!r} is already registered"
                    )
                self._store[reg_key] = obj
                logger.debug("Registered via decorator %s -> %s", reg_key, type(obj))
            return obj

        return decorator

    def clear(self) -> None:
        """Remove all entries from the registry."""
        with self._lock:
            self._store.clear()
            logger.debug("Registry cleared")

    def remove(self, key: K) -> None:
        """Alias for deleting a key (raises NotRegisteredError if
        missing)."""
        with self._lock:
            if key in self._store:
                del self._store[key]
                logger.debug("Unregistered %s", key)
            else:
                raise NotRegisteredError(f"Registry key {key!r} is not registered")

    def get(self, key: K, default: Any = None) -> Any:
        with self._lock:
            return self._store.get(key, default)

    def snapshot(self) -> Dict[K, V]:
        """Return a shallow copy of the internal mapping.

        Useful for safe iteration without locks. Note: copy is shallow, so
        mutable values are still shared.
        """
        with self._lock:
            return dict(self._store)

    # Serialization helpers
    def to_dict(self) -> Dict[K, V]:
        # shallow copy that is safe to mutate by caller
        return self.snapshot()

    @classmethod
    def from_dict(cls, data: Mapping[K, V]) -> "Registry[K, V]":
        r = cls()
        with r._lock:
            r._store.update(dict(data))
        return r

    def to_json(self, **kwargs: Any) -> str:
        """Serialize registry to JSON string.

        Accepts the same keyword arguments as `json.dumps` (forwards them).
        Raises TypeError if values are not JSON serializable.
        """
        # WARNING: values must be JSON serializable or override this method
        return json.dumps(self.to_dict(), **kwargs)

    @classmethod
    def from_json(cls, s: str, **kwargs: Any) -> "Registry[K, V]":
        """Construct a Registry from JSON string. Forwards kwargs to
        `json.loads`."""
        return cls.from_dict(json.loads(s, **kwargs))

    # Context manager for bulk operations
    def bulk(self) -> ContextManager["Registry[K, V]"]:
        """Return a context manager that yields this registry while holding
        the lock.

        Example:
            with registry.bulk() as reg:
                # reg is the same Registry instance and lock is held
                reg["k"] = 1

        The context manager will not suppress exceptions (returns False
        from __exit__).
        """

        class _Ctx:
            def __init__(self, r: "Registry[K, V]"):
                self._r: "Registry[K, V]" = r
                self._lock: RLock = r._lock

            def __enter__(self) -> "Registry[K, V]":
                self._lock.acquire()
                return self._r

            def __exit__(self, exc_type, exc, tb):
                self._lock.release()
                return False

        return _Ctx(self)

    # Pickle support (store is picklable if values are picklable)
    def __getstate__(self):
        # Only persist the mapping; lock is re-created on unpickle
        return {"_store": dict(self._store)}

    def __setstate__(self, state):
        self._lock = RLock()
        self._store = state.get("_store", {})
