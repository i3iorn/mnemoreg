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

from mnemoreg.exceptions import AlreadyRegisteredError, NotRegisteredError

K = TypeVar("K", bound=str)
V = TypeVar("V")

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)


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
        >>> registry = Registry[str, int]()
        >>> registry['a'] = 1
        >>> registry['a']
        1
        >>> @registry.register('b')
        ... def value_b():
        ...     return 2
        >>> registry['b']()
        2
    """

    def __init__(self, *, lock: Optional[RLock] = None) -> None:
        self._lock: RLock = lock or RLock()
        self._store: Dict[K, V] = {}

    # Mapping protocol
    def __getitem__(self, key: K) -> V:
        with self._lock:
            try:
                return self._store[key]
            except KeyError:
                raise NotRegisteredError(f"Registry key {key!r} is not registered")

    def __setitem__(self, key: K, value: V) -> None:
        with self._lock:
            if key in self._store:
                raise AlreadyRegisteredError(
                    f"Registry key {key!r} is already registered"
                )
            self._store[key] = value
            logger.debug("Registered %s -> %s", key, type(value))

    def __delitem__(self, key: K) -> None:
        with self._lock:
            if key in self._store:
                del self._store[key]
                logger.debug("Unregistered %s", key)
            else:
                raise NotRegisteredError(f"Registry key {key!r} is not registered")

    def __iter__(self) -> Iterator[K]:
        with self._lock:
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

    def register(self, key: Optional[K] = None) -> Callable[[V], V]:
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
        with self._lock:
            self._store.clear()
            logger.debug("Registry cleared")

    def remove(self, key: K) -> None:
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
        with self._lock:
            return dict(self._store)

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

    def bulk(self) -> ContextManager["Registry[K, V]"]:
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

    def __getstate__(self):
        return {"_store": dict(self._store)}

    def __setstate__(self, state):
        self._lock = RLock()
        self._store = state.get("_store", {})
