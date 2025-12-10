import contextlib
import json
import logging
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
    Type,
    cast,
    overload,
)

from mnemoreg import AlreadyRegisteredError, NotRegisteredError, StorageProtocol
from mnemoreg._types import K, Stored, V
from mnemoreg.core.stored_item import StoredItem
from mnemoreg.core.utils import OverwritePolicy, _make_default_store, locked_method

logger = logging.getLogger(__name__)


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
            hasattr(lock, method)
            for method in ("__enter__", "__exit__", "acquire", "release")
        ):
            raise TypeError("lock must be a threading.RLock or similar object")

        if not (50 >= log_level >= 0):
            raise ValueError("log_level must be a valid logging level between 0 and 50")

        self._lock: RLock = lock or RLock()
        # Use a typed helper so the concrete MemoryStorage() construction
        # does not introduce Any/Union into the annotated type of self._store.
        self._store: StorageProtocol[K, V] = (
            store if store is not None else _make_default_store()
        )
        self._overwrite_policy = OverwritePolicy(overwrite_policy)
        logger.setLevel(log_level)

    def register(
        self, key: Optional[K] = None, description: Optional[str] = None
    ) -> Callable[[V], V]:
        """
        Decorator to register an object with the given key.

        Args:
            key: The key to register the object under. If None, the object's
                 `__name__` attribute will be used.
            description: Optional description for the registered object.
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

            description_str = description
            if not isinstance(description_str, str) and description_str is not None:
                description_str = str(description_str)
            if description_str is None:
                description_str = f"Registered object of type {type(obj).__name__}"

            with self._lock:
                # store under the resolved reg_key
                self._store.set(reg_key, obj, description=description_str)
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
        stored = self._store.get(key, default)
        v, _ = stored
        return v

    @locked_method
    def snapshot(self) -> Dict[K, StoredItem[Optional[V]]]:
        out: Dict[K, StoredItem[Optional[V]]] = {}
        for k in self._store.keys():
            v, d = self._store.get(k)  # v: Optional[V], d: Optional[str]
            out[k] = StoredItem(v, d)
        return out

    def to_dict(self) -> Dict[K, Optional[V]]:
        snap = self.snapshot()
        return {k: item.value for k, item in snap.items()}

    @overload
    @classmethod
    def from_dict(
        cls: Type["Registry[K, V]"], data: Mapping[K, Stored[V]]
    ) -> "Registry[K, V]": ...

    @overload
    @classmethod
    def from_dict(
        cls: Type["Registry[K, V]"], data: Mapping[K, V]
    ) -> "Registry[K, V]": ...

    @classmethod
    def from_dict(cls, data: Mapping[K, Any]) -> "Registry[K, Any]":
        """
        Create a Registry from a dictionary.

        Raises:
            TypeError: If the input data is not a mapping.
        """
        r = cls()
        with r._lock:
            # accept Mapping[K, V] or Mapping[K, Stored[V]]; coerce to Stored[Any]
            normalized: Dict[K, Stored[Any]] = {}
            for k, v in data.items():
                if isinstance(v, tuple) and len(v) == 2:
                    normalized[k] = cast(Stored[Any], v)
                else:
                    normalized[k] = (cast(Optional[Any], v), None)
            r._store.update(normalized)
        return cast("Registry[K, Any]", r)

    def to_json(self, **kwargs: Any) -> str:
        """
        Serialize the registry to a JSON string.

        Raises:
            TypeError: If the registry contains non-serializable values.
        """
        return json.dumps(self.to_dict(), **kwargs)

    @classmethod
    def from_json(cls, s: str, **kwargs: Any) -> "Registry[K, Any]":
        """
        Deserialize a JSON string to create a Registry.

        Raises:
            json.JSONDecodeError: If the input string is not valid JSON.
        """
        return cls.from_dict(json.loads(s, **kwargs))

    @locked_method
    def update(self, data: Mapping[K, Any]) -> None:
        """
        Update the registry with multiple key-value pairs.

        Raises:
            TypeError: If any key is not a valid string.
        """
        for k, vd in data.items():
            if isinstance(vd, tuple) and len(vd) == 2:
                v, d = vd
            else:
                v, d = (cast(Optional[V], vd), None)
            self._validate_key(k, cant_exist=self._overwrite_policy == 0)
            self._store.set(k, v, d)

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
        stored = self._store.get(key)
        v, _ = stored
        if v is None:
            raise NotRegisteredError(f"Registry key {key!r} is not registered")
        return v

    @locked_method
    def __setitem__(self, key: K, value: V) -> None:
        self._validate_key(key, cant_exist=self._overwrite_policy == 0)
        # no description provided when setting via mapping assignment
        self._store.set(key, value, description=None)
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
