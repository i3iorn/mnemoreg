import contextlib
import json
import logging
from enum import IntEnum
from threading import RLock
from typing import (
    Any,
    Callable,
    ContextManager,
    Dict,
    Generic,
    Iterable,
    Mapping,
    MutableMapping,
    Optional,
)

from mnemoreg._storage import MemoeryStorage, StorageProtocol
from mnemoreg._types import K, V
from mnemoreg.exceptions import AlreadyRegisteredError, NotRegisteredError

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)


def locked_method(method: Callable) -> Callable:
    """Decorator to lock method calls for thread safety."""

    def wrapper(self: "Registry", *args: Any, **kwargs: Any) -> Any:
        with self._lock:
            return method(self, *args, **kwargs)

    return wrapper


class OverwritePolicy(IntEnum):
    FORBID = 0
    ALLOW = 1
    WARN = 2


class Registry(MutableMapping, Generic[K, V]):
    """
    Thread-safe registry implementing MutableMapping.

    Arguments:
        lock: Optional lock object to use for synchronization. If None,
            a new RLock is created for threadsafe operation.

    Raises:
        AlreadyRegisteredError: If attempting to register a key that already exists.
        NotRegisteredError: If attempting to access or delete a key that does not exist.

    Examples:
        >>> from typing import Callable
        >>> registry = Registry[str, Callable[[int], int]]()
        >>> registry['a'] = (lambda x: x)  # store a callable
        >>> registry['a'](1)
        1
        >>> @registry.register('b')
        ... def value_b(x: int) -> int:
        ...     return x + 1
        >>> registry['b'](2)
        3
    """

    def __init__(
        self,
        *,
        lock: Optional[RLock] = None,
        log_level: int = logging.WARNING,
        overwrite_policy: int = OverwritePolicy.FORBID,
        store: Optional[StorageProtocol] = None,
    ) -> None:
        # Verify  that lock has the correct methods
        if lock is not None and not all(
            hasattr(lock, method) for method in ("__enter__", "__exit__")
        ):
            raise TypeError("lock must be a threading.RLock or similar object")

        if not (50 >= log_level >= 0):
            raise ValueError("log_level must be a valid logging level between 0 and 50")

        self._lock: RLock = lock or RLock()
        self._store = store or MemoeryStorage()
        self._overwrite_policy = OverwritePolicy(overwrite_policy)
        logger.setLevel(log_level)

    def register(self, key: Optional[K] = None) -> Callable[[V], V]:
        """
        Decorator to register an object with the given key.

        Args:
            key: The key to register the object under. If None, the object's
                 `__name__` attribute will be used.
        Returns:
            A decorator that registers the object and returns it.

        Raises:
            ValueError: If the key is not provided and cannot be inferred
                        from the object.
        """

        def decorator(obj: V) -> V:
            reg_key = key if key is not None else getattr(obj, "__name__", None)
            if reg_key is None:
                raise ValueError(
                    "Registry key must be provided or inferable from object"
                )
            self._validate_key(reg_key, cant_exist=self._overwrite_policy == 0)

            with self._lock:
                # store under the resolved reg_key
                self._store.set(reg_key, obj)
                logger.debug("Registered via decorator %s -> %s", reg_key, type(obj))
            return obj

        return decorator

    def unregister(self, key: K) -> None:
        """Alias for __delitem__ to unregister a key."""
        self.__delitem__(key)

    def remove(self, key: K) -> None:
        """Alias for __delitem__ to remove a key."""
        self.__delitem__(key)

    @locked_method
    def clear(self) -> None:
        self._store.clear()
        logger.debug("Registry cleared")

    @locked_method
    def get(self, key: K, default: Any = None) -> Any:
        return self._store.get(key, default)

    @locked_method
    def snapshot(self) -> Dict[K, V]:
        return self._store.to_dict()

    def to_dict(self) -> Dict[K, V]:
        return self.snapshot()

    @classmethod
    def from_dict(cls, data: Mapping[K, V]) -> "Registry[K, V]":
        r = cls()
        with r._lock:
            r._store.update(dict(data))
        return r

    def to_json(self, **kwargs: Any) -> str:
        return json.dumps(self.to_dict(), **kwargs)

    @classmethod
    def from_json(cls, s: str, **kwargs: Any) -> "Registry[K, V]":
        return cls.from_dict(json.loads(s, **kwargs))

    @locked_method
    def update(self, data: Mapping[K, V]) -> None:
        for k, v in data.items():
            self._validate_key(k, cant_exist=self._overwrite_policy == 0)
            self._store.set(k, v)

    def bulk(self) -> ContextManager["Registry[K, V]"]:
        @contextlib.contextmanager
        def _bulk_ctx():
            self._lock.acquire()
            try:
                yield self
            finally:
                self._lock.release()

        return _bulk_ctx()

    def _validate_key(
        self, key: K, cant_exist: bool = False, must_exist: bool = False
    ) -> None:
        if not isinstance(key, str):
            raise TypeError(f"Registry key must be a string, got {type(key)}")
        elif not key:
            raise ValueError("Registry key cannot be an empty string")
        elif any(c.isspace() for c in key):
            raise ValueError("Registry key cannot contain whitespace characters")
        elif cant_exist and key in self._store.keys():
            raise AlreadyRegisteredError(f"Registry key {key!r} is already registered")
        elif must_exist and key not in self._store.keys():
            raise NotRegisteredError(f"Registry key {key!r} is not registered")

    @locked_method
    def __getitem__(self, key: K) -> V:
        self._validate_key(key, must_exist=True)
        res = self._store.get(key)
        if res is None:
            raise NotRegisteredError(f"Registry key {key!r} is not registered")
        return res

    @locked_method
    def __setitem__(self, key: K, value: V) -> None:
        self._validate_key(key, cant_exist=self._overwrite_policy == 0)
        self._store.set(key, value)
        logger.debug("Registered %s -> %s", key, type(value))

    @locked_method
    def __delitem__(self, key: K) -> None:
        self._validate_key(key, must_exist=True)
        self._store.delete(key)

    @locked_method
    def __iter__(self) -> Iterable[K]:
        return iter(list(self._store.keys()))

    @locked_method
    def __len__(self) -> int:
        return len(self._store)

    @locked_method
    def __contains__(self, key: object) -> bool:
        return key in self._store

    @locked_method
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({list(self._store.keys())!r})"

    def __getstate__(self):
        return {"_store": self._store.to_dict()}

    def __setstate__(self, state):
        self._lock = RLock()
        self._store.update(state.get("_store", {}))
