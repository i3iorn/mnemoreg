import contextlib
import json
import logging
from dataclasses import dataclass
from enum import IntEnum
from threading import RLock
from typing import (
    Any,
    Callable,
    ContextManager,
    Dict,
    Generic,
    Iterable,
    Iterator,
    Mapping,
    MutableMapping,
    Optional,
    cast,
)

from mnemoreg._storage import MemoeryStorage, StorageProtocol
from mnemoreg._types import K, V
from mnemoreg.exceptions import AlreadyRegisteredError, NotRegisteredError

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)


def _make_default_store() -> StorageProtocol[K, V]:
    """Create a default StorageProtocol[K, V] instance.

    Construct the concrete MemoeryStorage() at runtime and cast it to the
    protocol with generics so the module-level type inference remains
    precise. Localizes the unavoidable cast to one place.
    """
    return cast(StorageProtocol[K, V], MemoeryStorage())


def locked_method(method: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to lock method calls for thread safety."""

    def wrapper(self: "Registry[K, V]", *args: Any, **kwargs: Any) -> Any:
        with self._lock:
            return method(self, *args, **kwargs)

    return wrapper


class OverwritePolicy(IntEnum):
    FORBID = 0
    ALLOW = 1
    WARN = 2


@dataclass
class StoredItem(Generic[V]):
    """Transparent wrapper for stored values returned by `snapshot()`.

    The wrapper stores a value in the `value` attribute but delegates
    attribute access and many common operations to the underlying value so
    code can treat a StoredItem like the wrapped object (e.g. a list and
    call .append on the StoredItem).
    """

    _value: Any

    def __init__(self, value: Optional[V]) -> None:
        self._value = value

    @property
    def value(self) -> Optional[V]:
        return cast(Optional[V], self._value)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._value, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name == "_value" or name.startswith("_") or name in type(self).__dict__:
            object.__setattr__(self, name, value)
        else:
            try:
                setattr(self._value, name, value)
            except Exception:
                object.__setattr__(self, name, value)

    def __repr__(self) -> str:  # pragma: no cover - trivial
        return f"{self.__class__.__name__}({self._value!r})"

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


class Registry(MutableMapping[K, V], Generic[K, V]):
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
        store: Optional[StorageProtocol[K, V]] = None,
    ) -> None:
        """
        Initialize the Registry.

        Args:
            lock: An optional threading.RLock or similar object for thread safety.
            log_level: Logging level for the registry logger.
            overwrite_policy: Policy for handling existing keys:
                0 - Forbid overwriting (default)
                1 - Allow overwriting
                2 - Warn on overwriting
            store: An optional storage backend implementing StorageProtocol.

        Raises:
            TypeError: If the provided lock does not implement context manager methods.
            ValueError: If log_level is not a valid logging level.

        Example:
            registry = Registry[str, int](log_level=logging.DEBUG, overwrite_policy=1)
        """
        if lock is not None and not all(
            hasattr(lock, method) for method in ("__enter__", "__exit__")
        ):
            raise TypeError("lock must be a threading.RLock or similar object")

        if not (50 >= log_level >= 0):
            raise ValueError("log_level must be a valid logging level between 0 and 50")

        self._lock: RLock = lock or RLock()
        # Use a typed helper so the concrete MemoeryStorage() construction
        # does not introduce Any/Union into the annotated type of self._store.
        self._store: StorageProtocol[K, V] = (
            store if store is not None else _make_default_store()
        )
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

    @locked_method
    def clear(self) -> None:
        """
        Clear all entries from the registry.
        """
        self._store.clear()
        logger.debug("Registry cleared")

    @locked_method
    def get(self, key: K, default: Optional[V] = None) -> Optional[V]:
        """
        Get the value for the given key, or return default if not found.
        """
        return self._store.get(key, default)

    @locked_method
    def snapshot(self) -> Dict[K, StoredItem[Optional[V]]]:
        out: Dict[K, StoredItem[Optional[V]]] = {}
        for k in self._store.keys():
            v = self._store.get(k)  # v: Optional[V]
            out[k] = StoredItem(v)
        return out

    def to_dict(self) -> Dict[K, Optional[V]]:
        snap = self.snapshot()
        return {k: item.value for k, item in snap.items()}

    @classmethod
    def from_dict(cls, data: Mapping[K, V]) -> "Registry[K, V]":
        """
        Create a Registry from a dictionary.

        Raises:
            TypeError: If the input data is not a mapping.
        """
        r = cls()
        with r._lock:
            r._store.update(dict(data))
        return r

    def to_json(self, **kwargs: Any) -> str:
        """
        Serialize the registry to a JSON string.

        Raises:
            TypeError: If the registry contains non-serializable values.
        """
        return json.dumps(self.to_dict(), **kwargs)

    @classmethod
    def from_json(cls, s: str, **kwargs: Any) -> "Registry[K, V]":
        """
        Deserialize a JSON string to create a Registry.

        Raises:
            json.JSONDecodeError: If the input string is not valid JSON.
        """
        return cls.from_dict(json.loads(s, **kwargs))

    @locked_method
    def update(self, data: Mapping[K, V]) -> None:
        """
        Update the registry with multiple key-value pairs.

        Raises:
            TypeError: If any key is not a valid string.
        """
        for k, v in data.items():
            self._validate_key(k, cant_exist=self._overwrite_policy == 0)
            self._store.set(k, v)

    def bulk(self) -> ContextManager["Registry[K, V]"]:
        """
        Context manager for bulk operations on the registry.

        Returns:
            A context manager that yields the registry for bulk operations.

        Usage:
            with registry.bulk() as reg:
                reg['key1'] = value1
                reg['key2'] = value2
        """

        @contextlib.contextmanager
        def _bulk_ctx() -> Iterator[Registry[K, V]]:
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

    def __getstate__(self) -> Dict[str, Any]:
        return {"_store": self._store.to_dict()}

    def __setstate__(self, state: Dict[str, Any]) -> None:
        self._lock = RLock()
        self._store.update(state.get("_store", {}))
