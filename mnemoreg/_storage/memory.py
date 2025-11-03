from typing import Dict, Generic, Iterator, Mapping, Optional

from mnemoreg._storage.base import AbstractStorage
from mnemoreg._types import K, V


class MemoeryStorage(AbstractStorage[K, V], Generic[K, V]):
    """A simple in-memory storage implementation using a dictionary."""

    def __init__(self) -> None:
        self._store: Dict[K, V] = {}

    def set(self, key: K, value: V) -> None:
        self._store[key] = value

    def get(self, key: K, default: Optional[V] = None) -> Optional[V]:
        return self._store.get(key, default)

    def delete(self, key: K) -> None:
        if key in self._store:
            del self._store[key]

    def clear(self) -> None:
        self._store.clear()

    def to_dict(self) -> Dict[K, V]:
        return dict(self._store)

    def update(self, data: Mapping[K, V]) -> None:
        self._store.update(data)

    def keys(self) -> Iterator[K]:
        return iter(self._store.keys())

    def __len__(self) -> int:
        return len(self._store)

    def __contains__(self, key: object) -> bool:
        return key in self._store
