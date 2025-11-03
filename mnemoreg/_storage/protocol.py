from typing import Any, Dict, Generic, Iterator, Mapping, Protocol, runtime_checkable

from mnemoreg._types import K, V


@runtime_checkable
class StorageProtocol(Protocol, Generic[K, V]):
    """Minimal protocol describing the storage interface expected by Registry.

    Only the methods and members that `mnemoreg.core.Registry` uses are
    specified here so the protocol stays small and permissive.
    """

    def set(self, key: K, value: V) -> None:  # pragma: no cover - interface
        ...

    def get(self, key: K, default: Any = None) -> Any:  # pragma: no cover - interface
        ...

    def delete(self, key: K) -> None:  # pragma: no cover - interface
        ...

    def clear(self) -> None:  # pragma: no cover - interface
        ...

    def to_dict(self) -> Dict[K, V]:  # pragma: no cover - interface
        ...

    def update(self, data: Mapping[K, V]) -> None:  # pragma: no cover - interface
        ...

    def keys(self) -> Iterator[K]:  # pragma: no cover - interface
        ...

    def __len__(self) -> int:  # pragma: no cover - interface
        ...

    def __contains__(self, key: object) -> bool:  # pragma: no cover - interface
        ...
