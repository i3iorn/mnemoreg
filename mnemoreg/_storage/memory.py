from typing import Dict, Generic, Iterator, Mapping, Optional

from mnemoreg._storage.base import AbstractStorage
from mnemoreg._types import K, Stored, V


class MemoryStorage(AbstractStorage[K, V], Generic[K, V]):
    """A simple in-memory storage implementation using a dictionary."""

    def __init__(self) -> None:
        self._store: Dict[K, Stored[V]] = {}

    def set(
        self, key: K, value: Optional[V], description: Optional[str] = None
    ) -> None:
        self._store[key] = (value, description)

    def get(self, key: K, default: Optional[V] = None) -> Stored[V]:
        return self._store.get(key, (default, None))

    def delete(self, key: K) -> None:
        if key in self._store:
            del self._store[key]

    def clear(self) -> None:
        self._store.clear()

    def to_dict(self) -> Dict[K, Stored[V]]:
        return dict(self._store)

    def update(self, data: Mapping[K, Stored[V]]) -> None:
        self._store.update(data)

    def keys(self) -> Iterator[K]:
        return iter(self._store.keys())

    def __len__(self) -> int:
        return len(self._store)

    def __contains__(self, key: object) -> bool:
        return key in self._store
