from abc import ABC, abstractmethod
from typing import Dict, Generic, Iterator, Mapping, Optional

from mnemoreg._types import K, Stored, V


class AbstractStorage(ABC, Generic[K, V]):
    """Abstract base class for storage implementations."""

    @abstractmethod
    def set(
        self, key: K, value: Optional[V], description: Optional[str] = None
    ) -> None:
        pass

    @abstractmethod
    def get(self, key: K, default: Optional[V] = None) -> Stored[V]:
        pass

    @abstractmethod
    def delete(self, key: K) -> None:
        pass

    @abstractmethod
    def clear(self) -> None:
        pass

    @abstractmethod
    def to_dict(self) -> Dict[K, Stored[V]]:
        pass

    @abstractmethod
    def update(self, data: Mapping[K, Stored[V]]) -> None:
        pass

    @abstractmethod
    def keys(self) -> Iterator[K]:
        pass

    @abstractmethod
    def __len__(self) -> int:
        pass

    @abstractmethod
    def __contains__(self, key: object) -> bool:
        pass
